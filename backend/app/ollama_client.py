import json
import logging
import time
from urllib.parse import urlparse, urlunparse

import requests
from .config import (
    LLM_PROVIDER,
    OLLAMA_URL,
    OLLAMA_MODEL,
    GEMINI_URL,
    GEMINI_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODELS,
    GEMINI_RETRY_COUNT,
    GEMINI_RETRY_BACKOFF,
    GEMINI_RETRY_BACKOFF_FACTOR,
    GEMINI_TIMEOUT,
    LLM_TIMEOUT,
)

# Prefer explicit localhost fallback for Ollama during local development.
# Use a fixed localhost fallback so the backend reliably retries the local service.
OLLAMA_LOCAL_FALLBACK = 'http://localhost:11434'
logger = logging.getLogger('agent.llm')


def _is_ollama_connection_error(exc):
    if isinstance(exc, requests.exceptions.ConnectionError):
        text = str(exc).lower()
        return 'failed to resolve' in text or 'getaddrinfo failed' in text or 'name resolution' in text
    return False


def _send_ollama_request(url: str, payload: dict, timeout: int, stream: bool = False):
    logger.warning('Ollama request url=%s stream=%s model=%s', url, stream, payload.get('model'))
    request_kwargs = {
        'json': payload,
        'timeout': timeout,
    }
    if stream:
        request_kwargs['stream'] = True

    try:
        response = requests.post(url, **request_kwargs)
        logger.debug('Ollama response status=%s', getattr(response, 'status_code', None))
        return response
    except requests.exceptions.ConnectionError as exc:
        fallback_url = OLLAMA_LOCAL_FALLBACK.rstrip('/') + '/v1/completions'
        logger.warning('Ollama connection error for url=%s: %s', url, exc)
        if url != fallback_url and ('ollama' in url or _is_ollama_connection_error(exc)):
            logger.warning('Retrying Ollama on local fallback url=%s', fallback_url)
            return requests.post(fallback_url, **request_kwargs)
        raise


def _get_gemini_models():
    models = []
    if GEMINI_MODEL:
        models.append(GEMINI_MODEL)
    for model in GEMINI_MODELS:
        if model and model not in models:
            models.append(model)
    return models


def _build_google_url(model: str) -> str:
    google_url = GEMINI_URL
    if not google_url or "generativelanguage.googleapis.com" not in google_url:
        google_url = "https://generativelanguage.googleapis.com/v1beta"
    if google_url.endswith(":generateContent"):
        return google_url
    return google_url.rstrip("/") + f"/models/{model}:generateContent"


def _extract_google_text(data):
    if not isinstance(data, dict):
        return json.dumps(data)
    candidates = data.get("candidates") or []
    if candidates and isinstance(candidates, list):
        c0 = candidates[0]
        content = c0.get("content")
        if isinstance(content, dict):
            if isinstance(content.get("text"), str) and content.get("text"):
                return content.get("text", "")
            parts = content.get("parts") or []
            if isinstance(parts, list) and parts:
                first = parts[0]
                if isinstance(first, dict) and isinstance(first.get("text"), str):
                    return first.get("text", "")
        elif isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                if isinstance(first.get("text"), str) and first.get("text"):
                    return first.get("text", "")
                parts = first.get("parts") or []
                if isinstance(parts, list) and parts and isinstance(parts[0], dict):
                    return parts[0].get("text", "")
    # Try nested and fallback fields
    if isinstance(data.get("output"), dict):
        output = data.get("output")
        if isinstance(output.get("text"), str) and output.get("text"):
            return output.get("text", "")
    for key in ("text", "result", "response"):
        v = data.get(key)
        if isinstance(v, str) and v:
            return v
    return json.dumps(data)


def _should_retry_exception(exc):
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return exc.response.status_code in {429, 502, 503, 504}
    return False


def _gemini_google_request(prompt: str, model: str):
    google_url = _build_google_url(model)
    headers = {"Content-Type": "application/json"}
    if GEMINI_API_KEY:
        headers["X-Goog-Api-Key"] = GEMINI_API_KEY
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    logger.info('Gemini Google request model=%s url=%s prompt_length=%s', model, google_url, len(prompt))

    last_exc = None
    for attempt in range(1, GEMINI_RETRY_COUNT + 1):
        try:
            response = requests.post(google_url, headers=headers, json=payload, timeout=LLM_TIMEOUT)
            response.raise_for_status()
            logger.debug('Gemini Google response status=%s model=%s', response.status_code, model)
            return response
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning('Gemini Google request failed (attempt %s/%s model=%s): %s', attempt, GEMINI_RETRY_COUNT, model, exc)
            if attempt < GEMINI_RETRY_COUNT and _should_retry_exception(exc):
                wait = GEMINI_RETRY_BACKOFF * (GEMINI_RETRY_BACKOFF_FACTOR ** (attempt - 1))
                logger.info('Retrying Gemini Google in %s seconds', wait)
                time.sleep(wait)
                continue
            break

    masked = '***' if GEMINI_API_KEY else '(no key)'
    raise RuntimeError(f"Gemini (Google) request failed (model={model}, url={google_url}, key={masked}): {last_exc}") from last_exc


def _gemini_openai_request(prompt: str, model: str, max_tokens: int, temperature: float):
    headers = {"Content-Type": "application/json"}
    if GEMINI_API_KEY:
        headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    logger.info('Gemini OpenAI request model=%s url=%s prompt_length=%s', model, GEMINI_URL, len(prompt))
    last_exc = None
    for attempt in range(1, GEMINI_RETRY_COUNT + 1):
        try:
            response = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=LLM_TIMEOUT)
            response.raise_for_status()
            logger.debug('Gemini OpenAI response status=%s model=%s', response.status_code, model)
            return response
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning('Gemini OpenAI request failed (attempt %s/%s model=%s): %s', attempt, GEMINI_RETRY_COUNT, model, exc)
            if attempt < GEMINI_RETRY_COUNT and _should_retry_exception(exc):
                wait = GEMINI_RETRY_BACKOFF * (GEMINI_RETRY_BACKOFF_FACTOR ** (attempt - 1))
                logger.info('Retrying Gemini OpenAI in %s seconds', wait)
                time.sleep(wait)
                continue
            break

    masked = '***' if GEMINI_API_KEY else '(no key)'
    raise RuntimeError(f"Gemini request failed (model={model}, url={GEMINI_URL}, key={masked}): {last_exc}") from last_exc


def _gemini_openai_streaming_request(prompt: str, model: str, max_tokens: int, temperature: float):
    headers = {"Content-Type": "application/json"}
    if GEMINI_API_KEY:
        headers["Authorization"] = f"Bearer {GEMINI_API_KEY}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    last_exc = None
    for attempt in range(1, GEMINI_RETRY_COUNT + 1):
        response = None
        try:
            response = requests.post(GEMINI_URL, headers=headers, json=payload, stream=True, timeout=LLM_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if response is not None:
                response.close()
            if attempt < GEMINI_RETRY_COUNT and _should_retry_exception(exc):
                wait = GEMINI_RETRY_BACKOFF * (GEMINI_RETRY_BACKOFF_FACTOR ** (attempt - 1))
                time.sleep(wait)
                continue
            break

    masked = '***' if GEMINI_API_KEY else '(no key)'
    raise RuntimeError(f"Gemini streaming request failed (model={model}, url={GEMINI_URL}, key={masked}): {last_exc}") from last_exc


def _call_gemini_google(prompt: str):
    errors = []
    for model in _get_gemini_models():
        try:
            response = _gemini_google_request(prompt, model)
            data = response.json()
            return _extract_google_text(data)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue

    raise RuntimeError("All Gemini Google models failed: " + " | ".join(errors))


def _extract_llm_text(data):
    if not isinstance(data, dict):
        text = str(data).strip()
        return text if text else ""

    for key in ("text", "response", "result", "answer"):  # common top-level text fields
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    choices = data.get("choices") or []
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

            for choice_key in ("text", "content", "response", "output"):  # handle response variants
                value = first_choice.get(choice_key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            output = first_choice.get("output")
            if isinstance(output, dict):
                for output_key in ("text", "content", "response"):
                    value = output.get(output_key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

    output = data.get("output")
    if isinstance(output, dict):
        for output_key in ("text", "content", "response"):
            value = output.get(output_key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def _call_gemini_openai(prompt: str, max_tokens: int, temperature: float):
    errors = []
    for model in _get_gemini_models():
        try:
            response = _gemini_openai_request(prompt, model, max_tokens, temperature)
            data = response.json()
            answer = _extract_llm_text(data)
            if not answer:
                raise RuntimeError('Gemini OpenAI returned an empty response body.')
            return answer
        except RuntimeError as exc:
            errors.append(str(exc))
            continue

    raise RuntimeError("All Gemini models failed: " + " | ".join(errors))


def _call_ollama(prompt: str, max_tokens: int, temperature: float) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    url = f"{OLLAMA_URL}/v1/completions"
    logger.warning('Calling Ollama provider model=%s url=%s prompt_length=%s', OLLAMA_MODEL, url, len(prompt))
    response = _send_ollama_request(url, payload, LLM_TIMEOUT, stream=False)
    response.raise_for_status()
    data = response.json()
    logger.debug('Ollama response data=%s', {k: v for k, v in data.items() if k != 'usage'})
    answer = _extract_llm_text(data)
    if not answer:
        logger.error('Ollama returned an empty reply. Response data=%s', json.dumps(data, default=str))
        raise RuntimeError('Ollama returned an empty response body.')
    return answer


def ask_llm(prompt: str, max_tokens: int = 1000, temperature: float = 0.2) -> str:
    logger.info('ask_llm provider=%s prompt_length=%s max_tokens=%s', LLM_PROVIDER, len(prompt), max_tokens)
    if LLM_PROVIDER.lower() == "gemini":
        use_google = False
        if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AQ."):
            use_google = True
        if "generativelanguage.googleapis.com" in (GEMINI_URL or ""):
            use_google = True

        if use_google:
            try:
                return _call_gemini_google(prompt)
            except RuntimeError as exc:
                logger.warning('Gemini Google failed, falling back to Ollama: %s', exc)
                logger.warning('Attempting Ollama fallback after Gemini Google failure')
                try:
                    return _call_ollama(prompt, max_tokens, temperature)
                except Exception as oexc:
                    logger.exception('Ollama fallback failed after Gemini Google error: %s', oexc)
                    raise

        try:
            return _call_gemini_openai(prompt, max_tokens, temperature)
        except RuntimeError as exc:
            logger.warning('Gemini OpenAI failed, falling back to Ollama: %s', exc)
            logger.warning('Attempting Ollama fallback after Gemini OpenAI failure')
            try:
                return _call_ollama(prompt, max_tokens, temperature)
            except Exception as oexc:
                logger.exception('Ollama fallback failed after Gemini OpenAI error: %s', oexc)
                raise

    logger.info('Using Ollama directly as fallback provider')
    return _call_ollama(prompt, max_tokens, temperature)


def stream_llm(prompt: str, max_tokens: int = 1000, temperature: float = 0.2):
    if LLM_PROVIDER.lower() == "gemini":
        use_google = False
        if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AQ."):
            use_google = True
        if "generativelanguage.googleapis.com" in (GEMINI_URL or ""):
            use_google = True

        if use_google:
            answer = ask_llm(prompt, max_tokens, temperature)
            yield f"data: {json.dumps({'text': answer})}\n\n"
            return

        for model in _get_gemini_models():
            try:
                with _gemini_openai_streaming_request(prompt, model, max_tokens, temperature) as response:
                    for line in response.iter_lines(decode_unicode=True):
                        if line:
                            yield f"data: {line}\n\n"
                return
            except RuntimeError:
                continue

        # Fall back to Ollama streaming if Gemini streaming fails
        try:
            url = f"{OLLAMA_URL}/v1/completions"
            with _send_ollama_request(url, {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }, LLM_TIMEOUT, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        yield f"data: {line}\n\n"
            return
        except Exception as exc:
            raise RuntimeError("All Gemini streaming models failed and Ollama fallback also failed") from exc

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    with requests.post(f"{OLLAMA_URL}/v1/completions", json=payload, stream=True, timeout=LLM_TIMEOUT) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if line:
                yield f"data: {line}\n\n"
