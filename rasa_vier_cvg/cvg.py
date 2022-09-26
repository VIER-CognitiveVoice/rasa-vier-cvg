import asyncio
from datetime import datetime
import logging
import inspect
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional, Text
import warnings

#ignore ResourceWarning, InsecureRequestWarning
warnings.filterwarnings("ignore", category=ResourceWarning)

from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

import rasa.shared.utils.io
from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage

from cvg_sdk.api_client import ApiClient
from cvg_sdk.api.call_api import CallApi
from cvg_sdk.api.assist_api import AssistApi
from cvg_sdk.configuration import Configuration
from cvg_sdk.model.say_parameters import SayParameters
from cvg_sdk.model.drop_parameters import DropParameters
from cvg_sdk.model.recording_start_parameters import RecordingStartParameters
from cvg_sdk.model.recording_stop_parameters import RecordingStopParameters
from cvg_sdk.model.play_parameters import PlayParameters
from cvg_sdk.model.transcription_switch_parameters import (
    TranscriptionSwitchParameters,
)  # noqa: E501, F401
from cvg_sdk.model.bridge_parameters import BridgeParameters
from cvg_sdk.model.forward_parameters import ForwardParameters
from cvg_sdk.model.prompt_parameters import PromptParameters

from cvg_sdk.model.inactivity_start_parameters import InactivityStartParameters  # noqa: E501, F401
from cvg_sdk.model.inactivity_stop_parameters import InactivityStopParameters

from cvg_sdk.model.accept_assist_parameters import AcceptAssistParameters
from cvg_sdk.model.transcription_start_parameters import (
    TranscriptionStartParameters,
)  # noqa: E501, F401
from cvg_sdk.model.transcription_stop_parameters import (
    TranscriptionStopParameters,
)  # noqa: E501, F401
from cvg_sdk.model.assist_recording_start_parameters import (
    AssistRecordingStartParameters,
)  # noqa: E501, F401
from cvg_sdk.model.assist_recording_stop_parameters import (
    AssistRecordingStopParameters,
)  # noqa: E501, F401

from cvg_sdk.model.outbound_call_result import OutboundCallResult
from cvg_sdk.model.outbound_call_success import OutboundCallSuccess
from cvg_sdk.model.outbound_call_failure import OutboundCallFailure

logger = logging.getLogger(__name__)

BOT_INACTIVITY_INTENT = "/cvg_bot_inactivity"
RESTART_INTENT = "/restart"

class CVGOutput(OutputChannel):
    """Output channel for the Cognitive Voice Gateway"""

    on_message: Callable[[UserMessage], Awaitable[Any]]

    @classmethod
    def name(cls) -> Text:
        return "cvg"

    def __init__(
        self, callback_base_url: Text, on_message: Callable[[UserMessage], Awaitable[Any]], proxy: Optional[Text] = None,
    ) -> None:  # noqa: E501, F401
        configuration = Configuration.get_default_copy()
        configuration.host = callback_base_url
        configuration.proxy = proxy
        configuration.verify_ssl = False

        self.on_message = on_message

        self.api_client = ApiClient(configuration=configuration)
        self.call_api = CallApi(self.api_client)
        self.assist_api = AssistApi(self.api_client)

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        logger.info("Sending message to cvg: %s" % text)
        logger.info("Ignoring the following args: " + str(kwargs))
        self.call_api.say(SayParameters(dialog_id=recipient_id, text=text))

    async def _execute_operation_by_name(
        self, operation_name: Text, body: Any, dialog_id: Text
    ):  # noqa: E501, F401
        def create_parameters(parameters_type: type):
            parameter_args = {}
            for (
                python_name,
                spec_name,
            ) in parameters_type.attribute_map.items():  # noqa: E501, F401
                if spec_name in body:
                    parameter_args[python_name] = body[spec_name]
                elif spec_name == "dialogId":
                    parameter_args[python_name] = dialog_id
                else:
                    logger.info(
                        "Parameter %s for endpoint %s not set."
                        % (spec_name, parameters_type.__name__)
                    )  # noqa: E501, F401
            return parameters_type(**parameter_args)

        async def handle_outbound_call_result(outbound_call_result: OutboundCallResult, success_text: Text, failure_text: Text):
            user_message : UserMessage = None
            if outbound_call_result.status == "Success":
                success_model : OutboundCallSuccess = outbound_call_result
                user_message = UserMessage(
                    text=success_text,
                    output_channel=self,
                    sender_id=dialog_id,
                    input_channel="cvg",
                    metadata={"cvg_body": success_model.to_dict()},
                )
            elif outbound_call_result.status == "Failure":
                failure_model : OutboundCallFailure = outbound_call_result
                user_message = UserMessage(
                    text=failure_text,
                    output_channel=self,
                    sender_id=dialog_id,
                    input_channel="cvg",
                    metadata={"cvg_body": failure_model.to_dict()},
                )
            else:
                return response.text(f"Invalid OutboundCallResult status: {outbound_call_result.status}", status=400)

            if user_message is not None:
                logger.info(
                    "Creating incoming UserMessage: {text=%s, output_channel=%s, sender_id=%s, metadata=%s}"  # noqa: E501, F401
                    % (user_message.text, user_message.output_channel, user_message.sender_id, user_message.metadata)  # noqa: E501, F401
                )
                await self.on_message(user_message)

        async def handle_bridge_response(outbound_call_result: OutboundCallResult):
            await handle_outbound_call_result(
                outbound_call_result=outbound_call_result,
                success_text="/bridge_successful",
                failure_text="/bridge_failed",
            )

        async def handle_forward_response(outbound_call_result: OutboundCallResult):
            await handle_outbound_call_result(
                outbound_call_result=outbound_call_result,
                success_text="/forward_successful",
                failure_text="/forward_failed",
            )

        if operation_name == "cvg_call_drop":
            self.call_api.drop(create_parameters(DropParameters))
        elif operation_name == "cvg_call_recording_start":
            self.call_api.start_recording(
                create_parameters(RecordingStartParameters)
            )  # noqa: E501, F401
        elif operation_name == "cvg_call_recording_stop":
            self.call_api.stop_recording(
                create_parameters(RecordingStopParameters)
            )  # noqa: E501, F401
        elif operation_name == "cvg_call_play":
            self.call_api.play(create_parameters(PlayParameters))
        elif operation_name == "cvg_call_transcription_switch":
            self.call_api.switch_transcription(
                create_parameters(TranscriptionSwitchParameters)
            )  # noqa: E501, F401
        elif operation_name == "cvg_call_bridge":
            await handle_bridge_response(
                self.call_api.bridge(create_parameters(BridgeParameters))
            )  # noqa: E501, F401
        elif operation_name == "cvg_call_forward":
            await handle_forward_response(
                self.call_api.forward(create_parameters(ForwardParameters))
            )  # noqa: E501, F401
        elif operation_name == "cvg_call_say":
            self.call_api.say(create_parameters(SayParameters))
        elif operation_name == "cvg_call_prompt":
            self.call_api.prompt(create_parameters(PromptParameters))
        elif operation_name == "cvg_inactivity_start":
            self.call_api.start_inactivity(create_parameters(InactivityStartParameters))
        elif operation_name == "cvg_inactivity_stop":
            self.call_api.stop_inactivity(create_parameters(InactivityStopParameters))

        elif operation_name == "cvg_assist_transcription_start":
            self.assist_api.start_transcription(
                create_parameters(TranscriptionStartParameters)
            ),  # noqa: E501, F401
        elif operation_name == "cvg_assist_transcription_stop":
            self.assist_api.stop_transcription(
                create_parameters(TranscriptionStopParameters)
            ),  # noqa: E501, F401
        elif operation_name == "cvg_assist_recording_start":
            self.assist_api.start_recording(
                create_parameters(AssistRecordingStartParameters)
            ),  # noqa: E501, F401
        elif operation_name == "cvg_assist_recording_stop":
            self.assist_api.stop_recording(
                create_parameters(AssistRecordingStopParameters)
            ),  # noqa: E501, F401
        else:
            logger.error(
                "Operation %s not found/not implemented yet" % operation_name
            )  # noqa: E501, F401
        logger.info("Ran operation: " + operation_name)

    async def send_custom_json(
        self,
        recipient_id: Text,
        json_message: Dict[Text, Any],
        **kwargs: Any,  # noqa: E501, F401
    ) -> None:
        logger.info(
            "Received custom json: %s to %s" % (json_message, recipient_id)
        )  # noqa: E501, F401
        for key, value in json_message.items():
            await self._execute_operation_by_name(
                operation_name=key, dialog_id=recipient_id, body=value
            )  # noqa: E501, F401

    async def send_image_url(self, **_: Any) -> None:
        rasa.shared.utils.io.raise_warning(
            "Ignoring image URL."
            "We cannot represent images as a voice bot."
            "Please define a voice-friendly alternative."
        ) # We do not support images.

class CVGInput(InputChannel):
    """Input channel for the Cognitive Voice Gateway"""

    @classmethod
    def name(cls) -> Text:
        return "cvg"

    @classmethod
    def from_credentials(
        cls, credentials: Optional[Dict[Text, Any]]
    ) -> InputChannel:  # noqa: E501, F401
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(
            credentials.get("proxy")
            )

    def __init__(self,
                 proxy: Optional[Text] = None
                 ) -> None:
        
        self.callback = None
        self.proxy = proxy

    # requires valid json in the request
    def get_metadata(self, request: Request) -> Dict[Text, Any]:
        return {
            "cvg_body": request.json
        }

    async def process_message(
        self,
        request: Request,
        on_new_message: Callable[[UserMessage], Awaitable[Any]],
        text: Text,
        sender_id: Optional[Text],
    ) -> Any:
        try:
            metadata = self.get_metadata(request)
            if text[-1] == ".":
                text = text[:-1]

            user_msg = UserMessage(
                text=text,
                output_channel=CVGOutput(metadata["cvg_body"]["callback"], on_new_message, self.proxy),
                sender_id=sender_id,
                input_channel=self.name(),
                metadata=metadata,
            )

            logger.info(
                "Creating incoming UserMessage: {text=%s, output_channel=%s, sender_id=%s, metadata=%s}"  # noqa: E501, F401
                % (text, user_msg.output_channel, sender_id, metadata)
            )

            await on_new_message(user_msg)
        except Exception as e:
            logger.error(f"Exception when trying to handle message.{e}")
            logger.error(str(e), exc_info=True)

        return response.text("")

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        def valid_json(func):
            def decorator(f):
                @wraps(f)
                async def decorated_function(request: HTTPResponse, *args, **kwargs):
                    if not request.headers.get("content-type") == "application/json":
                        return response.text(
                            "content-type is not supported. Please use application/json",  # noqa: E501, F401
                            status=415,
                        )  # noqa: E501, F401
                    if request.json is None:
                        return response.text(
                            "body is not valid json.",
                            status=400
                        )
                    if request.json["dialogId"] is None:
                        return response.text(
                            "dialogId is required",
                            status=400
                        )
                    if request.json["callback"] is None:
                        return response.text(
                            "callback is required",
                            status=400
                        )
                    return await f(request, *args, **kwargs)
                return decorated_function
            return decorator(func)

        async def process_message_oneline(request: Request, text: Text): # This needs to be an async function
            return await self.process_message( # This needs to be waited as process_message is an async function
                request,
                on_new_message,
                text=text,
                sender_id=request.json["dialogId"],
            )
            

        cvg_webhook = Blueprint(
            "custom_webhook_{}".format(type(self).__name__),
            inspect.getmodule(self).__name__,
        )

        @cvg_webhook.get("/")
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @cvg_webhook.post("/session")
        @valid_json
        async def session(request: Request) -> HTTPResponse:
            bot_configuration = request.json["configuration"]
            if "session_starter" not in bot_configuration:
                return response.text("session_starter not set in BotConfiguration", status=400)
            return await process_message_oneline(request, "/" + bot_configuration["session_starter"])
        
        @cvg_webhook.post("/message")
        @valid_json
        async def message(request: Request) -> HTTPResponse:
            
            sender = request.json["dialogId"]
            message = request.json["text"]
            
            return await process_message_oneline(request, message)

        @cvg_webhook.post("/answer")
        @valid_json
        async def answer(request: Request) -> HTTPResponse:
            
            answer_type = request.json["type"]
            
            if answer_type["name"] == "MultipleChoice":
                payload = answer_type["id"]
            elif answer_type["name"] == "Number":
                payload = answer_type["value"]
            elif answer_type["name"] == "Timeout":
                payload = BOT_INACTIVITY_INTENT
            else:
                return response.text(f"Invalid Answer Type Object: {answer_type} Received", status=400)
            return await process_message_oneline(request, payload)

        @cvg_webhook.post("/inactivity")
        @valid_json
        async def inactivity(request: Request) -> HTTPResponse:
            """
            The /inactivity endpoint is called when the user has been inactive for a certain amount of time.
            The inactivity timeout is configured in the BotConfiguration.
            Once the inactivity timeout is reached, the bot calls an intent with the name `BOT_INACTIVITY_INTENT`.
            This is currently mapped to the custom `action_cvg_bot_inactivity` which
            in turn calls the `utter_cvg_bot_inactivity` response in the domain.yml.
            User can customize this behavior by changing the utterance in the domain.yml or by modifying the custom action.
            """
            
            return await process_message_oneline(request, BOT_INACTIVITY_INTENT)

        @cvg_webhook.post("/terminated")
        @valid_json
        async def terminated(request: Request) -> HTTPResponse:
            """
            When the call was terminated, we need to make sure that we clear the
            conversation state for the user. This is done by sending a 
            `RESTART_INTENT` to the bot. This is the last step of the conversation.
            And the bot will clear the conversation state.
            """
            return await process_message_oneline(request, RESTART_INTENT)

        @cvg_webhook.post("/recording")
        @valid_json
        async def recording(request: Request) -> HTTPResponse:
            """
            We need not give any response to the user in the recording endpoint.
            But we need to make sure to return the correct status code along with record id if available in the response.
            """
            
            recording_status = request.json["status"]
            recording_id = request.json["id"]
            
            return response.raw(f"Recording Status : {recording_status}, Recording ID: {recording_id}", status=204)

        @cvg_webhook.post("/webhook")
        async def webhook(request: Request) -> HTTPResponse:
            sender_id = await self._extract_sender(request)
            text = self._extract_message(request)

            collector = self.get_output_channel()
            await on_new_message(
                UserMessage(text, collector, sender_id, input_channel=self.name())  # noqa: E501, F401
            )
            return response.text("success")

        return cvg_webhook
