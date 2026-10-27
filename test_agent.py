import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from google.genai import types

from agent import run_agent


def tool_response(name, arguments, call_id="call-1"):
    call = types.FunctionCall(
        id=call_id,
        name=name,
        args=arguments,
    )
    content = types.Content(
        role="model",
        parts=[types.Part(function_call=call)],
    )

    return SimpleNamespace(
        candidates=[SimpleNamespace(content=content)],
        function_calls=[call],
    )


def text_response(text):
    content = types.Content(
        role="model",
        parts=[types.Part.from_text(text=text)],
    )

    return SimpleNamespace(
        candidates=[SimpleNamespace(content=content)],
        function_calls=[],
        text=text,
    )


class AgentTests(unittest.TestCase):
    def test_booking_tool_round_trip(self):
        client = Mock()

        first_response = tool_response(
            "get_booking",
            {"booking_id": "CW-1002"},
        )

        def model_reply(**kwargs):
            history = kwargs["contents"]

            if client.models.generate_content.call_count == 1:
                self.assertEqual(history[0].role, "user")
                return first_response

            # Verify that the tool result is returned to the model.
            message = history[-1]
            self.assertEqual(message.role, "user")

            result = message.parts[0].function_response
            self.assertEqual(result.id, "call-1")
            self.assertEqual(result.name, "get_booking")
            self.assertTrue(result.response["found"])
            self.assertEqual(
                result.response["booking"]["bike_type"],
                "e-bike",
            )
            self.assertEqual(result.response["booking"]["bikes"], 2)

            return text_response("There are 2 e-bikes.")

        client.models.generate_content.side_effect = model_reply

        answer = run_agent(
            client,
            "fake-model",
            "What bike is booked under CW-1002?",
        )

        self.assertEqual(answer, "There are 2 e-bikes.")
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_repeated_tool_calls_stop_at_limit(self):
        client = Mock()
        client.models.generate_content.return_value = tool_response(
            "get_booking",
            {"booking_id": "CW-1002"},
        )

        answer = run_agent(
            client,
            "fake-model",
            "Check my booking",
        )

        self.assertEqual(client.models.generate_content.call_count, 5)
        self.assertIn("limit was reached", answer)


if __name__ == "__main__":
    unittest.main()
