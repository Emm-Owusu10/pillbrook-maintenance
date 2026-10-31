"""Measure how long password hashing takes on this computer: python -m app.measure_hashing"""
import time

from .passwords import hash_password, verify_password

ROUNDS = 5
SAMPLE = "a long throwaway sample passphrase used only for timing"


def main() -> None:
    stored = hash_password(SAMPLE)

    start = time.perf_counter()
    for _ in range(ROUNDS):
        hash_password(SAMPLE)
    hashing_ms = (time.perf_counter() - start) / ROUNDS * 1000

    start = time.perf_counter()
    for _ in range(ROUNDS):
        verify_password(stored, SAMPLE)
    checking_ms = (time.perf_counter() - start) / ROUNDS * 1000

    print(f"Creating a password hash takes about {hashing_ms:.0f} ms on this computer.")
    print(f"Checking a password at login takes about {checking_ms:.0f} ms.")
    print("Between 50 and 500 ms is a good range.")


if __name__ == "__main__":
    main()