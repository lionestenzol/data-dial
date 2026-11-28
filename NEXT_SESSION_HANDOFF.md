# Hand-off — data-dial — next session

This document is written in ASD-STE100 Simplified Technical English.
It tells a new session the state of the project. It also gives the next task.

---

## 1. What the project is

data-dial moves files between two devices.
For each file, the system sends the cheapest correct form.

There are four forms:

- a key, if the far device has the bytes;
- a difference, if the far device has an older version;
- a recipe, if the far device can make the bytes again;
- the raw bytes, if no other form is possible.

The system makes the bytes again only when it can prove the result is correct.
It compares the SHA-256 hash of the new bytes with the hash of the file.
If the two hashes are not equal, the system sends the raw bytes.

The goal is simple.
When the connection is thin, slow, or costly, send as few bytes as possible.
Use local compute in place of bandwidth.

A fallback is one event.
A fallback occurs when the system sends the raw bytes because another form failed.

---

## 2. What is done

The engine works on one machine.
Two folders are device A and device B.
Nothing crosses a network.
The system counts the bytes that a real network would send.

All four forms work.
The system verifies each result byte-for-byte.

The regenerate form is the new work in this session.
Before, the project only scored this form.
Now the engine runs it.

These are the demo results:

- One photo of 357 kilobytes crossed as a recipe of 84 bytes.
- The demo moved 21 times fewer bytes on regenerable data.
- The demo used no fallback.

The tests pass.
The result is 12 tests pass and 1 test skips.
The test skips because this container has no rsync program.

---

## 3. Key files

- `dial/` — the engine. It works on one machine.
- `dial/generators.py` — the regenerate form. It has the recipe type and the generator list.
- `dial/router.py` — the chooser. Step 2.5 is the generate step.
- `dial/checker.py` — the receiver. The function `_on_generate` runs the generator. It then verifies the result.
- `dial/engine.py` — the run loop. It attaches a recipe to a file. It does this only when device A kept the recipe and device B can run the generator.
- `dial/device.py` — a device. It holds `provenance` for the A side and `can_generate` for the B side.
- `dial_gen_demo.py` — the demo. Run it to see the regenerate form work.
- `tests/test_generate_arm.py` — the tests for the regenerate form and the fallback.
- `ROADMAP.md` — the rungs. It shows the plan and the next rung.
- `HANDOFF.md` — the full project state. Read it for the history and the research notes.

---

## 4. How to run the code

To run the tests, do these steps:

1. Set the variable `PYTHONPATH` to `/home/user/data-dial`.
2. Run the command `python3 -m pytest tests/ -q`.

To run the demo, do these steps:

1. Run the command `PYTHONPATH=/home/user/data-dial python3 dial_gen_demo.py --n 8`.
2. Read the table. It shows the bytes for the arm OFF and the arm ON.

NOTE: If an import fails, install the package `zstandard`.
The engine needs this package.

---

## 5. The next task — rung 1

Move the engine off one machine.
Make the engine run between two devices over a real network.

Do these steps:

1. Add a transport. The transport sends one message over a socket.
2. Keep the message form and the byte count the same as now.
3. Run device A in one process.
4. Run device B in a second process.
5. Sync a folder between the two processes.
6. Verify that each file on device B is byte-exact.

The task is done when all of these are true:

- You sync a folder between two devices over a socket.
- Each file on device B is byte-exact.
- You can show the result to another person.

The decision gate is one question.
Does the system work after it leaves one machine?
If the answer is yes, build the shared hub. The shared hub is rung 2.

---

## 6. Rules

Obey these rules.

- Develop only on the branch `ccr-9a0cbe07-g58x1f`.
- Do not create a pull request. Create a pull request only if the user asks.
- End each commit message with these two lines:
  - `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  - `Claude-Session: https://claude.ai/code/session_01DESc3asewcqwsMXZQi1mqu`
- Do not put a model name in a commit, a file, or a code comment.
- Do not commit a secret.
- Keep the user data private. Do not send the user data to an external service without permission.

---

## 7. The open question

One question decides the value of the project.
How much of real data is regenerable or already held?

New data that you cannot make again must cross the pipe one time, at full size.
Measure this fraction.
The ledger calls this question `O-provenance-freq`.
