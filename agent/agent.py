import sys
import os
import json

from tools import get_drive_history, get_fleet_baseline, run_sql
from tool_defs import TOOLS
from prompts import SYSTEM_PROMPT
from dotenv import load_dotenv   # a tool that reads the .env file
import anthropic                  # Claude's library

load_dotenv()                     # load .env into environment variables

client = anthropic.Anthropic()    # creates a connection; finds ANTHROPIC_API_KEY automatically
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")
TOOL_FUNCTIONS = {
    "get_drive_history": get_drive_history,
    "get_fleet_baseline": get_fleet_baseline,
    "run_sql": run_sql,
}


def write_report(serial_number):
    
    
    messages = [{"role": "user", "content": f"Write an FA report for drive {serial_number}"}]
    for i in range(10):
        response = client.messages.create(
            model = MODEL,
            max_tokens = 3000,
            system = SYSTEM_PROMPT,
            tools = TOOLS,
            messages = messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            report_parts = []
            for block in response.content:
                if block.type == "text":
                    report_parts.append(block.text)
            return "\n".join(report_parts)


        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"Calling {block.name} with {block.input}")
                function = TOOL_FUNCTIONS[block.name]
                result = function(**block.input)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

        messages.append({"role": "user", "content": tool_results})

    return "Stopped: reached the 10-turn limit without finishing."



    
if __name__ == "__main__":
    serial_number = sys.argv[1]
    report = write_report(serial_number)
    os.makedirs("reports", exist_ok=True)          # create folder if missing
    path = f"reports/{serial_number}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to {path}")