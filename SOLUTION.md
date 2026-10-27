# CityWheels Help Desk Agent

A Python command-line assistant that answers CityWheels questions using
local policy documents and booking data.

## Setup and commands

Tested with Python 3.15.0. The dependencies require Python 3.10 or newer;
other Python versions have not been tested.

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini API key to `.env`:

```dotenv
AI_API_KEY=your_key_here
AI_MODEL=gemini-3.5-flash-lite
```

The application reads these variables explicitly. The real `.env` file
is excluded from Git.

Run the assistant:

```bash
python agent.py
```

Run all unit tests without an API key or network access:

```bash
python -m unittest discover -v
```

Run the evaluation using the real model:

```bash
python evaluate.py
```

Results are saved to `eval/results.json` after each question.
A new run overwrites the previous report.

## Model and provider

The assistant uses Google's Gemini API with `gemini-3.5-flash-lite`
through the `google-genai` SDK.

I chose it because it supports function calling and offers a free tier.
During development, requests to `gemini-3.8-flash` repeatedly returned
503 errors. Switching to Flash-Lite produced successful responses.

Availability and quotas depend on the API project. The evaluator spaces
request starts at least five seconds apart to reduce rate-limit errors.
Other activity in the same project may still consume the shared quota.

## How the agent works

The model receives the question, system instructions and descriptions
of three tools:

- `get_booking`: retrieves a booking or returns `found=false`.
- `calculate_refund`: calculates eligibility, rental and deposit refunds,
  and refund methods.
- `search_policies`: retrieves up to three relevant Markdown sections.

Automatic function execution in the SDK is disabled. The agent implements
the loop explicitly:

1. Send conversation history and tool declarations to the model.
2. Receive a final answer or one or more function calls.
3. Validate the tool name and required arguments.
4. Execute the Python functions.
5. Return their results to the model and continue.

The loop allows at most five model requests per question. Full model
messages and function-call IDs are preserved when returning results.

The system instructions restrict answers to CityWheels, require tools
for factual questions, prohibit invented booking details and amounts,
and direct unsupported requests to staff.

Refund amounts are calculated in Python using `Decimal`. The fixed
current time is 2026-06-10 09:00 Europe/Warsaw, as specified in the data.
Calculating a refund does not cancel a booking or transfer money.

Policy search uses keyword overlap, simple word normalization and a
higher score for matches in section headings.

## Tests and evaluation

The 14 unit tests cover booking lookup, refund rules, payment methods,
policy search and the agent loop.

Agent-loop tests use a fake model. They verify that actual booking data
is returned with the correct function-call ID and message role, and
that repeated tool requests stop at the configured limit.

The evaluation contains ten questions covering booking lookup,
unknown bookings, three refund scenarios, opening hours, age limits
and three requests the assistant should refuse.

Automatic checks inspect executed tools, booking IDs, expected facts,
amounts and forbidden answer content. Full answers and tool traces
are retained for manual review.

### Results and improvements

The initial evaluation produced:

- 8 passed checks.
- 1 failed answer about opening hours.
- 1 API error during the age-limit scenario.

The search treated `opening` and `open`, and `limit` and `limits`, as
different words. Relevant sections were omitted from the top results.
I added simple normalization and increased the weight of heading
matches. Regression tests cover the queries that exposed these failures.

The API error was a 429 response reporting a 15-request-per-minute
limit. Pausing between questions was insufficient because one question
can generate multiple model requests. Request pacing was moved around
each model call in the evaluator.

The latest evaluation passed 10/10 automatic checks. Its answers were
also manually reviewed against the supplied data.

## Use of AI coding assistance

I used Codex to discuss the design, generate code examples, explain
SDK behavior, review saved changes and run offline checks. I transferred
and ran the code locally and inspected the outputs.

AI-generated code required corrections:

- An example used the unsupported Gemini message role `tool`. The API
  returned HTTP 400. The role was changed to `user`, with the result
  represented as a `function_response`.
- Initial amount-checking expressions accepted `340.99` when `340.00`
  was expected. Additional offline checks exposed this. The expressions
  were tightened, then corrected to allow sentence-ending punctuation.
- An early timeout handler did not catch the exception wrapped by the
  Interactions API. The diagnostic request was moved to
  `models.generate_content`, with explicit timeout and error handling.

An early manual test also answered an unrelated geography question.
I clarified the scope instructions and retested unrelated and
instruction-override requests.

## Limitations and next steps

- Keyword search does not fully understand synonyms or language.
- The automated evaluation is heuristic: matching facts and amounts
  does not prove that every statement or association is correct.
- Passing ten scenarios does not guarantee consistent behavior on
  unseen requests.
- Scope restrictions rely on model instructions.
- API overload and rate limits can still interrupt requests.
- Each CLI run handles one question without follow-up conversation memory.
- Booking data is a supplied local fixture; no authentication or real
  booking modification is implemented.

With more time, I would expand evaluation with unseen paraphrases,
weather exceptions and additional refund boundary cases, improve
retrieval, and add bounded retries that respect provider retry guidance.
