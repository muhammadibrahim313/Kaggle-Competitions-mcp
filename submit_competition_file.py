import argparse
import http.cookiejar
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


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

    raise RuntimeError("No Kaggle token found. Use --token, set KAGGLE_TOKEN/kaggle_mcp_token, or create a token file.")


def decode_sse_payload(raw_text: str) -> dict:
    data_lines = []
    for line in raw_text.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not data_lines:
        raise RuntimeError(f"Unexpected MCP response: {raw_text[:500]}")
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
                "name": "submit_competition_file.py",
                "version": "1.0",
            },
        },
    }
    post_json(body, token)


def parse_tool_result(response: dict):
    result = response.get("result", {})
    if result.get("isError"):
        messages = []
        for item in result.get("content", []):
            if isinstance(item, dict) and "text" in item:
                messages.append(item["text"])
        raise RuntimeError("\n".join(messages) if messages else json.dumps(response))

    content = result.get("content", [])
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
    lower_keys = {key.lower() for key in candidate_keys}

    def walk(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                if key.lower() in lower_keys:
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


def upload_file(upload_url: str, file_path: Path) -> None:
    data = file_path.read_bytes()
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(data)),
        "Content-Range": f"bytes 0-{len(data) - 1}/{len(data)}",
    }
    req = urllib.request.Request(upload_url, data=data, headers=headers, method="PUT")
    with OPENER.open(req) as resp:
        status = getattr(resp, "status", None) or resp.getcode()
        if status not in (200, 201):
            raise RuntimeError(f"Upload failed with HTTP {status}")


def poll_submission(ref: int, token: str, interval: int, timeout: int):
    start = time.time()
    last_status = None
    while True:
        submission = call_tool("get_competition_submission", {"ref": ref}, token)
        status = find_value(submission, ["status"]) or "UNKNOWN"
        if status != last_status:
            print(f"status: {status}")
            last_status = status

        if status in {"COMPLETE", "ERROR", "CANCELLED", "STUCK", "PUBLIC", "PRIVATE"}:
            return submission

        if time.time() - start >= timeout:
            return submission
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Upload and submit a competition file through Kaggle MCP.")
    parser.add_argument("--competition", required=True, help="Competition slug, for example: titanic")
    parser.add_argument("--file", required=True, help="Local file to upload, for example: submission.csv")
    parser.add_argument("--description", required=True, help="Submission description")
    parser.add_argument("--token", default="", help="Kaggle token starting with KGAT")
    parser.add_argument("--token-file", default="token", help="Path to a file containing the Kaggle token")
    parser.add_argument("--poll-interval", type=int, default=5, help="Seconds between status checks")
    parser.add_argument("--timeout", type=int, default=120, help="Max seconds to wait for final submission status")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise FileNotFoundError(f"Submission file not found: {file_path}")

    token = load_token(args.token, args.token_file)
    initialize(token)

    start_response = call_tool(
        "start_competition_submission_upload",
        {
            "competitionName": args.competition,
            "fileName": file_path.name,
            "contentLength": file_path.stat().st_size,
            "lastModifiedEpochSeconds": int(file_path.stat().st_mtime),
        },
        token,
    )

    upload_url = find_value(
        start_response,
        ["createUrl", "create_url", "uploadUrl", "upload_url", "resumableUploadUrl", "resumable_upload_url"],
    )
    blob_file_tokens = find_value(start_response, ["blobFileTokens", "blob_file_tokens"])

    if not upload_url:
        raise RuntimeError(f"Could not find upload URL in response: {json.dumps(start_response, indent=2)}")
    if not blob_file_tokens:
        raise RuntimeError(f"Could not find blobFileTokens in response: {json.dumps(start_response, indent=2)}")

    print(f"uploading: {file_path.name} ({file_path.stat().st_size} bytes)")
    upload_file(upload_url, file_path)
    print("upload complete")

    submit_response = call_tool(
        "submit_to_competition",
        {
            "competitionName": args.competition,
            "submissionDescription": args.description,
            "blobFileTokens": blob_file_tokens,
        },
        token,
    )

    ref = find_value(submit_response, ["ref"])
    message = find_value(submit_response, ["message"])
    if not ref:
        raise RuntimeError(f"Could not find submission ref in response: {json.dumps(submit_response, indent=2)}")

    if message:
        print(message)
    print(f"submission ref: {ref}")

    final_submission = poll_submission(ref, token, args.poll_interval, args.timeout)
    print(json.dumps(final_submission, indent=2))


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
