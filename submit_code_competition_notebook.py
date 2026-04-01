import argparse
import http.cookiejar
import json
import os
import sys
from pathlib import Path
import urllib.error
import urllib.request


MCP_URL = "https://www.kaggle.com/mcp"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))


def load_token(explicit_token: str, token_file: str) -> str:
    if explicit_token:
        return explicit_token.strip().strip('"').strip("'").lstrip("\ufeff")

    for env_var in ["KAGGLE_TOKEN", "kaggle_mcp_token"]:
        env_token = os.getenv(env_var, "").strip()
        if env_token:
            return env_token.strip('"').strip("'").lstrip("\ufeff")

    token_path = Path(token_file)
    if token_path.exists():
        return token_path.read_text(encoding="utf-8-sig").strip().strip('"').strip("'").lstrip("\ufeff")

    dotenv_path = Path(".env")
    if dotenv_path.exists():
        for line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            if k.strip().lower() in {"kaggle_token", "kaggle_mcp_token"}:
                value = v.strip().strip('"').strip("'").lstrip("\ufeff")
                if value:
                    return value

    raise RuntimeError("No Kaggle token found. Use --token, set KAGGLE_TOKEN/kaggle_mcp_token, or create a token/.env file.")


def decode_sse_payload(raw_text: str) -> dict:
    data_lines = []
    for line in raw_text.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not data_lines:
        return json.loads(raw_text)
    return json.loads("\n".join(data_lines))


def post_json(body: dict, token: str) -> dict:
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with OPENER.open(req) as resp:
        return decode_sse_payload(resp.read().decode("utf-8"))


def initialize(token: str) -> None:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "submit_code_competition_notebook.py",
                "version": "1.0",
            },
        },
    }
    post_json(body, token)


def parse_tool_result(response: dict):
    result = response.get("result", {})
    if result.get("isError"):
        content = result.get("content", [])
        if isinstance(content, str):
            raise RuntimeError(content)
        messages = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                messages.append(item["text"])
        raise RuntimeError("\n".join(messages) if messages else json.dumps(response))

    content = result.get("content", [])
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content

    if not content:
        return result

    texts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
            texts.append(item["text"])

    if len(texts) == 1:
        text = texts[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return texts


def call_tool(tool_name: str, request_payload: dict, token: str):
    body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "request": request_payload,
            },
        },
    }
    return parse_tool_result(post_json(body, token))


def find_value(obj, candidate_keys):
    wanted = {key.lower() for key in candidate_keys}

    def walk(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                if key.lower() in wanted:
                    return inner
            for inner in value.values():
                found = walk(inner)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for inner in value:
                found = walk(inner)
                if found is not None:
                    return found
        return None

    return walk(obj)


def main():
    parser = argparse.ArgumentParser(description="Submit a notebook version to a Kaggle code competition through MCP.")
    parser.add_argument("--competition", required=True, help="Competition slug, for example: arc-prize-2026-arc-agi-2")
    parser.add_argument("--owner", required=True, help="Notebook owner username")
    parser.add_argument("--slug", required=True, help="Notebook slug")
    parser.add_argument("--kernel-version", type=int, default=0, help="Notebook version to submit; 0 means auto-discover")
    parser.add_argument("--file-name", default="submission.json", help="Output file name from the notebook run")
    parser.add_argument("--description", required=True, help="Submission description")
    parser.add_argument("--token", default="", help="Kaggle token starting with KGAT")
    parser.add_argument("--token-file", default="token", help="Path to a file containing the Kaggle token")
    args = parser.parse_args()

    token = load_token(args.token, args.token_file)
    initialize(token)

    kernel_version = args.kernel_version
    if kernel_version <= 0:
        notebook_info = call_tool(
            "get_notebook_info",
            {
                "userName": args.owner,
                "kernelSlug": args.slug,
            },
            token,
        )
        kernel_version = find_value(notebook_info, ["current_version_number", "currentVersionNumber", "version_number", "versionNumber"])
        if not kernel_version:
            raise RuntimeError(f"Could not determine notebook version from get_notebook_info response: {json.dumps(notebook_info, indent=2)}")

    response = call_tool(
        "create_code_competition_submission",
        {
            "competitionName": args.competition,
            "kernelOwner": args.owner,
            "kernelSlug": args.slug,
            "kernelVersion": int(kernel_version),
            "hasKernelVersion": True,
            "fileName": args.file_name,
            "hasFileName": True,
            "submissionDescription": args.description,
            "hasSubmissionDescription": True,
        },
        token,
    )

    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = ""
        print(f"HTTP error: {exc.code}", file=sys.stderr)
        if details:
            print(details, file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
