import os
import sys
from dotenv import load_dotenv
from google import genai
import argparse
from google.genai import types
from prompts import system_prompt
from call_function import available_functions, call_function

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
if api_key is None:
    raise RuntimeError("There's no API key")

MAX_ITERS = 20


def main():
    parser = argparse.ArgumentParser(description="Chatbot")
    parser.add_argument("user_prompt", type=str, help="User prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    messages: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=args.user_prompt)])
    ]

    if args.verbose:
        print(f"User prompt: {args.user_prompt}")

    for i in range(MAX_ITERS):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0,
                tools=[available_functions],
            ),
        )

        if args.verbose:
            prompt_tokens = response.usage_metadata.prompt_token_count
            response_tokens = response.usage_metadata.candidates_token_count
            print(f"Prompt tokens: {prompt_tokens}")
            print(f"Response tokens: {response_tokens}")

        # Append every candidate content the model produced this turn
        if response.candidates:
            for candidate in response.candidates:
                messages.append(candidate.content)

        if not response.function_calls:
            print("Final response:")
            print(response.text)
            return

        for tool_call in response.function_calls:
            result_message = call_function(tool_call, args.verbose)
            if (
                not result_message.parts
                or not result_message.parts[0].function_response
                or not result_message.parts[0].function_response.response
            ):
                raise Exception("Fatal: function call result missing content")
            if args.verbose:
                print(f"-> {result_message.parts[0].function_response.response}")
            messages.append(result_message)

    print(f"Error: Max iterations ({MAX_ITERS}) reached without a final response.")
    sys.exit(1)


if __name__ == "__main__":
    main()