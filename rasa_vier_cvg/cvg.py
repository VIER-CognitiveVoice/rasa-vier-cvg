import asyncio
import copy
import json
import base64
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional, Text, TypeVar, Coroutine, Set
import warnings
import aiohttp

# ignore ResourceWarning, InsecureRequestWarning
warnings.filterwarnings("ignore", category=ResourceWarning)

from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

import rasa.shared.utils.io
from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage

logger = logging.getLogger(__name__)

CHANNEL_NAME = "vier-cvg"
OPERATION_PREFIX = "cvg_"
DIALOG_ID_FIELD = "dialogId"
PROJECT_CONTEXT_FIELD = "projectContext"
RESELLER_TOKEN_FIELD = "resellerToken"
PROJECT_TOKEN_FIELD = "projectToken"
CALLBACK_FIELD = "callback"

T = TypeVar('T')


def make_metadata(payload: T) -> Dict[str, T]:
    return {"cvg_body": payload}


def parse_recipient_id(recipient_id: Text) -> (str, str, str):
    parsed_json = json.loads(base64.b64decode(bytes(recipient_id, 'utf-8')).decode('utf-8'))
    if type(parsed_json) is not list or len(parsed_json) != 3:
        raise ValueError('The given recipient id is incompatible with this output!')

    return parsed_json[2], parsed_json[1], parsed_json[0]


def create_recipient_id(reseller_token, project_token, dialog_id) -> Text:
    json_representation = json.dumps([
        dialog_id,
        project_token,
        reseller_token,
    ], separators=(',', ':'))
    return base64.b64encode(bytes(json_representation, 'utf-8')).decode('utf-8')


class TaskContainer:
    tasks: Set[asyncio.Task] = set()

    def run(self, coro: Coroutine[Any, Any, None]):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


class CVGOutput(OutputChannel):
    """Output channel for the Cognitive Voice Gateway"""

    on_message: Callable[[UserMessage], Awaitable[Any]]
    base_url: str
    proxy: Optional[str]
    task_container: TaskContainer = TaskContainer()

    @classmethod
    def name(cls) -> Text:
        return CHANNEL_NAME

    def __init__(self, callback_base_url: Text, on_message: Callable[[UserMessage], Awaitable[Any]], proxy: Optional[str] = None) -> None:
        self.on_message = on_message

        self.base_url = callback_base_url.rstrip('/')
        self.proxy = proxy

    # This functionality can be used to ignore certain messages received by this channel.
    # It can be used as a workaround for dialog setups that produce messages that should not be forwarded to CVG but still be tracked.
    # Due to a bug in rasa, this feature is required:
    # Normally, when a custom rasa action returns a response, it is sent to the current channel and gets added to the tracker.
    # However, returning an Event, it should only get added to the tracker, not sent to the channel. I believe this is a bug.
    # If you want to maintain an accurate history in the tracker when using the CVG API directly, we have to send an event.
    # Now, to prevent sending the message to CVG twice, this flag can be set to true so that the channel drops the message.
    def _is_ignored(self, custom_json) -> bool:
        return custom_json is not None and "ignore" in custom_json and custom_json["ignore"] == True

    async def _perform_request(self, path: str, method: str, data: Optional[any], dialog_id: Optional[str], retries: int = 0) -> (Optional[int], any):
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.request(method, url, json=data, proxy=self.proxy) as res:
                status = res.status
                if status == 204:
                    return status, {}

                body = await res.json()
                if status < 200 or status >= 300:
                    logger.error(f"{dialog_id} - Failed to send text message to CVG via {url}: status={status}, body={body}")

                return status, body
        except aiohttp.ClientResponseError as e:
            logger.error(f"{dialog_id} - Failed to send text message to CVG via {url}: status={e.status}, message={e.message}")
        except aiohttp.ClientConnectionError:
            if retries < 3:
                logger.error(f"{dialog_id} - The connection failed, retrying...")
                await self._perform_request(path, method, data, dialog_id, retries + 1)
            else:
                logger.error(f"{dialog_id} - {retries} retries all failed, that's it!")

    def _perform_request_async(self, path: str, method: str, data: Optional[any], dialog_id: Optional[str], process_result: Callable[[int, any], Coroutine[Any, Any, None]]):
        async def perform():
            status, body = await self._perform_request(path, method, data, dialog_id)
            await process_result(status, body)

        self.task_container.run(perform())

    async def _say(self, dialog_id: str, text: str):
        if len(text.strip()) > 0:
            await self._perform_request("/call/say", method="POST", data={DIALOG_ID_FIELD: dialog_id, "text": text}, dialog_id=dialog_id)

    async def send_text_message(self, recipient_id: Text, text: Text, custom, **kwargs: Any) -> None:
        if self._is_ignored(custom):
            return

        reseller_token, project_token, dialog_id = parse_recipient_id(recipient_id)
        logger.info(f"{dialog_id} - Sending text to say: {text}")
        await self._say(dialog_id, text)

    async def _handle_refer_result(self, status_code: int, result: Dict, dialog_id: Text, recipient_id: Text):
        if 200 <= status_code < 300:
            logger.info(f"{dialog_id} - Refer request succeeded: {status_code} with body {result}")
            return

        user_message = UserMessage(
            text="/cvg_refer_failure",
            output_channel=self,
            sender_id=recipient_id,
            input_channel=CHANNEL_NAME,
            metadata=make_metadata(result),
        )

        logger.info(f"{dialog_id} - Creating incoming UserMessage: text={user_message.text}, output_channel={user_message.output_channel}, sender_id={user_message.sender_id}, metadata={user_message.metadata}")
        await self.on_message(user_message)

    async def _handle_bridge_result(self, status_code: int, result: Dict, dialog_id: Text, recipient_id: Text):
        if not 200 <= status_code < 300:
            logger.info(f"{dialog_id} - Bridge request failed: {status_code} with body {result}")
            return

        status = result["status"]
        if status == "Success":
            user_message = UserMessage(
                text="/cvg_outbound_success",
                output_channel=self,
                sender_id=recipient_id,
                input_channel=CHANNEL_NAME,
                metadata=make_metadata(result),
            )
        elif status == "Failure":
            user_message = UserMessage(
                text="/cvg_outbound_failure",
                output_channel=self,
                sender_id=recipient_id,
                input_channel=CHANNEL_NAME,
                metadata=make_metadata(result),
            )
        else:
            logger.info(f"{dialog_id} - Invalid bridge result: {status}")
            return

        logger.info(f"{dialog_id} - Creating incoming UserMessage: text={user_message.text}, output_channel={user_message.output_channel}, sender_id={user_message.sender_id}, metadata={user_message.metadata}")
        await self.on_message(user_message)

    async def _execute_operation_by_name(self, operation_name: Text, body: Any, recipient_id: Text):
        reseller_token, project_token, dialog_id = parse_recipient_id(recipient_id)
        logger.info(f"{dialog_id} - Execute action {operation_name} with body: {body}")

        if body is None:
            new_body = {}
        else:
            new_body = copy.deepcopy(body)

        if operation_name.startswith("call_"):
            if DIALOG_ID_FIELD not in new_body:
                new_body[DIALOG_ID_FIELD] = dialog_id

            path = '/' + operation_name.replace('_', '/')

            # The response from forward and bridge must be handled
            handle_result_outbound_call_result_for = ["call_forward", "call_bridge"]
            if operation_name in handle_result_outbound_call_result_for:
                async def handle_outbound(status_code, response_body):
                    await self._handle_bridge_result(status_code, response_body, dialog_id, recipient_id)
                callback = handle_outbound
            elif operation_name == 'call_refer':
                async def handle_refer(status_code, response_body):
                    await self._handle_refer_result(status_code, response_body, dialog_id, recipient_id)
                callback = handle_refer
            else:
                async def do_nothing(*args):
                    pass
                callback = do_nothing

            self._perform_request_async(path, method="POST", data=new_body, dialog_id=dialog_id, process_result=callback)

        elif operation_name.startswith("dialog_"):
            if operation_name == "dialog_delete":
                await self._perform_request(f"/dialog/{reseller_token}/{dialog_id}", method="DELETE", data=new_body, dialog_id=dialog_id)
            elif operation_name == "dialog_data":
                await self._perform_request(f"/dialog/{reseller_token}/{dialog_id}/data", method="POST", data=new_body, dialog_id=dialog_id)
            else:
                logger.error(f"{dialog_id} - Dialog operation {operation_name} not found/not implemented yet.")
                return
        else:
            logger.error(f"{dialog_id} - Operation {operation_name} not found/not implemented yet.")
            return
        logger.info(f"{dialog_id} - Operation {operation_name} complete")

    async def send_custom_json(self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any) -> None:
        if self._is_ignored(json_message):
            return

        for operation_name, body in json_message.items():
            if operation_name[:len(OPERATION_PREFIX)] == OPERATION_PREFIX:
                await asyncio.sleep(0.050)
                await self._execute_operation_by_name(operation_name[len(OPERATION_PREFIX):], body, recipient_id)

    async def send_image_url(*args: Any, **kwargs: Any) -> None:
        # We do not support images.
        rasa.shared.utils.io.raise_warning(
            "Ignoring image URL."
            "We cannot represent images as a voice bot."
            "Please define a voice-friendly alternative."
        )


class CVGInput(InputChannel):
    """Input channel for the Cognitive Voice Gateway"""

    callback: Optional[str]
    start_intent: str
    proxy: Optional[str]
    expected_authorization_header_value: str
    blocking_endpoints: bool
    ignore_messages_when_busy: bool
    task_container: TaskContainer = TaskContainer()
    # This Set is not thread safe. However, sanic is not multithreaded.
    ignore_messages_for: set[Text] = set()

    @classmethod
    def name(cls) -> Text:
        return CHANNEL_NAME

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> InputChannel:
        if not credentials:
            cls.raise_missing_credentials_exception()
        token = credentials.get("token")
        if token is None or not isinstance(token, str) or len(token) == 0:
            raise ValueError('No authentication token has been configured in your credentials.yml!')
        proxy = credentials.get("proxy")
        start_intent = credentials.get("start_intent")
        if start_intent is None:
            start_intent = "/cvg_session"
        blocking_endpoints = credentials.get("blocking_endpoints")
        if blocking_endpoints is None:
            blocking_endpoints = True
        else:
            blocking_endpoints = bool(blocking_endpoints)

        ignore_messages_when_busy = credentials.get("ignore_messages_when_busy")
        if ignore_messages_when_busy is None:
            ignore_messages_when_busy = False
        else:
            ignore_messages_when_busy = bool(ignore_messages_when_busy)

        logger.info(f"Creating input with: token={'*' * len(token)} proxy={proxy} start_intent={start_intent} blocking_endpoints={blocking_endpoints} ignore_messages_when_busy={ignore_messages_when_busy}")
        return cls(token, start_intent, proxy, blocking_endpoints, ignore_messages_when_busy)

    def __init__(self, token: Text, start_intent: Text, proxy: Optional[Text], blocking_endpoints: bool, ignore_messages_when_busy: bool) -> None:
        self.callback = None
        self.expected_authorization_header_value = f"Bearer {token}"
        self.proxy = proxy
        self.start_intent = start_intent
        self.blocking_endpoints = blocking_endpoints
        self.ignore_messages_when_busy = ignore_messages_when_busy

    async def _process_message(self, request: Request, on_new_message: Callable[[UserMessage], Awaitable[Any]], dialog_id: Text, text: Text, sender_id: Text) -> Any:
        try:
            if text[-1] == ".":
                text = text[:-1]

            metadata = make_metadata(request.json)
            user_msg = UserMessage(
                text=text,
                output_channel=CVGOutput(request.json[CALLBACK_FIELD], on_new_message, self.proxy),
                sender_id=sender_id,
                input_channel=CHANNEL_NAME,
                metadata=metadata,
            )

            # Ignore Messages when busy uses a local variable to check if there is already a message being processed.
            # This means that this feature does NOT work with multiple instances of this channel/rasa handling the same sender_id.
            if (self.ignore_messages_when_busy):
                if (dialog_id in self.ignore_messages_for):
                    logger.warning(f"{dialog_id} - A message is already being processed for this dialog and ignore_messages_when_busy is True. Ignoring message from User: '{text}'")
                    return response.empty(204)
                else:
                    self.ignore_messages_for.add(dialog_id)

            logger.info(f"{dialog_id} - Creating incoming UserMessage: text={text}, output_channel={user_msg.output_channel}, sender_id={sender_id}, metadata={metadata}")
            try:
                await on_new_message(user_msg)
            finally:
                if (self.ignore_messages_when_busy):
                    self.ignore_messages_for.remove(dialog_id)
        except Exception as e:
            logger.error(f"{dialog_id} - Exception when trying to handle message: {e}")
            logger.error(e, exc_info=True)

        return response.empty(204)

    def blueprint(self, on_new_message: Callable[[UserMessage], Awaitable[Any]]) -> Blueprint:
        def valid_request(func):
            def decorator(f):
                @wraps(f)
                async def decorated_function(request: HTTPResponse, *args, **kwargs):
                    if request.headers.get("authorization") != self.expected_authorization_header_value:
                        return response.text("bot token is invalid!", status=401)

                    if not request.headers.get("content-type") == "application/json":
                        return response.text("content-type is not supported. Please use application/json", status=415)
                    json_body = request.json
                    if json_body is None:
                        return response.text("body is not valid json.", status=400)
                    if json_body[DIALOG_ID_FIELD] is None:
                        return response.text(f"{DIALOG_ID_FIELD} is required", status=400)
                    if json_body[CALLBACK_FIELD] is None:
                        return response.text(f"{CALLBACK_FIELD} is required", status=400)
                    if PROJECT_CONTEXT_FIELD not in json_body:
                        return response.text(f"{PROJECT_CONTEXT_FIELD} is required", status=400)
                    else:
                        project_context = json_body[PROJECT_CONTEXT_FIELD]
                        if RESELLER_TOKEN_FIELD not in project_context:
                            return response.text(f'The {RESELLER_TOKEN_FIELD} is required in {PROJECT_CONTEXT_FIELD}!')
                        if PROJECT_TOKEN_FIELD not in project_context:
                            return response.text(f'The {PROJECT_TOKEN_FIELD} is required in {PROJECT_CONTEXT_FIELD}!')

                    return await f(request, *args, **kwargs)
                return decorated_function
            return decorator(func)

        async def _process_request(request: Request, text: Text, must_block: bool):
            dialog_id = request.json[DIALOG_ID_FIELD]
            sender_id = create_recipient_id(
                request.json[PROJECT_CONTEXT_FIELD][RESELLER_TOKEN_FIELD],
                request.json[PROJECT_CONTEXT_FIELD][PROJECT_TOKEN_FIELD],
                dialog_id
            )

            result = self._process_message(
                request,
                on_new_message,
                dialog_id,
                text,
                sender_id,
            )

            if self.blocking_endpoints or must_block:
                await result
            else:
                self.task_container.run(result)

            return response.empty(204)
            
        cvg_webhook = Blueprint(
            "vier_cvg_webhook", __name__,
        )

        @cvg_webhook.post("/session")
        @valid_request
        async def session(request: Request) -> HTTPResponse:
            await _process_request(request, self.start_intent, True)
            return response.json({"action": "ACCEPT"}, 200)
        
        @cvg_webhook.post("/message")
        @valid_request
        async def message(request: Request) -> HTTPResponse:
            return await _process_request(request, request.json["text"], False)

        @cvg_webhook.post("/answer")
        @valid_request
        async def answer(request: Request) -> HTTPResponse:
            return await _process_request(request, "/cvg_answer_" + request.json["type"]["name"].lower(), False)

        @cvg_webhook.post("/inactivity")
        @valid_request
        async def inactivity(request: Request) -> HTTPResponse:
            return await _process_request(request, "/cvg_inactivity", False)

        @cvg_webhook.post("/terminated")
        @valid_request
        async def terminated(request: Request) -> HTTPResponse:
            return await _process_request(request, "/cvg_terminated", False)

        @cvg_webhook.post("/recording")
        @valid_request
        async def recording(request: Request) -> HTTPResponse:
            return await _process_request(request, "/cvg_recording", False)

        return cvg_webhook
