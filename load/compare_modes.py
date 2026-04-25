import argparse
import asyncio
import csv
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx


BASE_URL = "http://127.0.0.1:8000"


@dataclass(slots=True)
class RequestResult:
    mode: str
    status_code: int
    response_ms: float


def aggregate(rows: list[RequestResult]) -> dict[str, int | float]:
    total = len(rows)
    success = sum(1 for row in rows if 200 <= row.status_code < 300)
    conflict = sum(1 for row in rows if row.status_code == 409)
    ms_values = [row.response_ms for row in rows]
    return {
        "total_requests": total,
        "success_count": success,
        "conflict_count": conflict,
        "avg_response_ms": round(statistics.mean(ms_values), 2) if ms_values else 0.0,
        "max_response_ms": round(max(ms_values), 2) if ms_values else 0.0,
    }


async def do_post(client: httpx.AsyncClient, path: str, payload: dict | None = None) -> httpx.Response:
    return await client.post(f"{BASE_URL}{path}", json=payload)


async def reset_and_seed(client: httpx.AsyncClient) -> None:
    await do_post(client, "/experiments/reset")
    await do_post(client, "/experiments/seed")


async def scenario_a(client: httpx.AsyncClient, mode: str) -> list[RequestResult]:
    results: list[RequestResult] = []
    base = datetime(2026, 4, 20, 10, 0, 0)

    for i in range(20):
        start = base + timedelta(hours=i)
        end = start + timedelta(minutes=45)
        payload = {
            "room_id": (i % 3) + 1,
            "user_id": (i % 3) + 1,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "mode": mode,
            "scenario": "A_sequential_no_conflict",
        }
        t0 = time.perf_counter()
        response = await do_post(client, "/bookings", payload)
        t1 = time.perf_counter()
        results.append(RequestResult(mode=mode, status_code=response.status_code, response_ms=(t1 - t0) * 1000))

    return results


async def scenario_b(client: httpx.AsyncClient, mode: str) -> list[RequestResult]:
    base = datetime(2026, 4, 21, 10, 0, 0)

    async def send_one(i: int) -> RequestResult:
        # Первые 10 идут в один слот/комнату -> частые конфликты.
        if i < 10:
            room_id = 1
            start = base
            end = base + timedelta(hours=1)
        else:
            room_id = ((i - 10) % 3) + 1
            start = base + timedelta(hours=i - 9)
            end = start + timedelta(hours=1)

        payload = {
            "room_id": room_id,
            "user_id": (i % 3) + 1,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "mode": mode,
            "scenario": "B_parallel_with_conflicts",
        }
        t0 = time.perf_counter()
        response = await do_post(client, "/bookings", payload)
        t1 = time.perf_counter()
        return RequestResult(mode=mode, status_code=response.status_code, response_ms=(t1 - t0) * 1000)

    return list(await asyncio.gather(*[send_one(i) for i in range(20)]))


async def run(output_csv: str, worker_delay_ms: int) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        await do_post(client, "/experiments/worker/on")
        await do_post(client, "/experiments/worker/delay", {"delay_ms": worker_delay_ms})

        all_rows: list[dict[str, str | int | float]] = []
        for mode in ("centralized_sync", "hybrid_async"):
            await reset_and_seed(client)

            a_rows = await scenario_a(client, mode)
            all_rows.append({"mode": f"{mode}:scenario_A", **aggregate(a_rows)})

            b_rows = await scenario_b(client, mode)
            all_rows.append({"mode": f"{mode}:scenario_B", **aggregate(b_rows)})

        with open(output_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "mode",
                    "total_requests",
                    "success_count",
                    "conflict_count",
                    "avg_response_ms",
                    "max_response_ms",
                ],
            )
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"Done. Results saved to: {output_csv}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare booking modes under basic load scenarios")
    parser.add_argument("--output", default="results.csv", help="Path to output CSV")
    parser.add_argument("--worker-delay-ms", type=int, default=0, help="Artificial worker delay in ms")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(output_csv=args.output, worker_delay_ms=args.worker_delay_ms))
