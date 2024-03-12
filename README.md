# Rasa and VIER Cognitive Voice Gateway

Rasa is the leading open-source conversational AI platform that enables both individual developers and large enterprises to build superior AI assistants and chatbots. Rasa provides the infrastructure and tools needed to build the outstanding tools and transform the way customers communicate with businesses. Rasa can be deeply customized down to levels not possible with other platforms due to the open sourced architecture and machine learning.

Rasa is used by millions of developers and small teams to program enterprise conversational AI applications.

Rasa is available in two editions: *Rasa Open Source* (free) and *Rasa Enterprise* (commercial). Both editions can be used to build voicebots with CVG.

[VIER Cognitive Voice Gateway (CVG)](https://cognitivevoice.io/docs) enables access to telephony, speech-to-text (STT), text-to-speech (TTS) and contact center integration for chatbots built with Rasa. I.e. CVG makes your chatbot to a voicebot handling phone calls.

To build voice bots using Rasa and CVG, you need an account in CVG and a Rasa installation.

### Installing Rasa

Rasa can be hosted anywhere: in the cloud, On-Prem or in any data center. Migrations between hosting solutions can be performed at any stage.

Many organizations developing chatbots and voicebots with Rasa start with Rasa Open Source On-Prem. An [installation guide](https://rasa.com/docs/rasa/installation/installing-rasa-open-source) is provided by Rasa. Rasa also provides a Playground that can be used to develop bots without requiring an On-Prem installation.

To install Rasa Enterprise, use the [installation guide](https://rasa.com/docs/rasa-enterprise/installation-and-setup/installation-guide) provided by Rasa.

### Installing VIER CVG Channel for Rasa

The Rasa integration with CVG is done with a new channel for Rasa provided in this repo.
It implements all the CVG APIs relevant for bots to provide CVGs full power to you as a Rasa developer.

The easiest way to install this package is through PyPI.

```
pip install rasa-vier-cvg
```

#### Docker

If you are using Rasa on Docker and you don't want to build a derived image, you can also download the [channel source](https://github.com/VIER-CognitiveVoice/rasa-vier-cvg/) and bind-mount the package into a `rasa/rasa`-base container with a volume definition like this:

```
./rasa_vier_cvg:/opt/venv/lib/python3.10/site-packages/rasa_vier_cvg
```

### Configure your Rasa Bot

Add the following content to `credentials.yml`:

```
rasa_vier_cvg.CVGInput:
  token: "CHOOSE_YOUR_TOKEN"
  blocking_endpoints: false
```
You can generate the token yourself. For example with any password generator.

This channel will be used for communication with CVG.
The Bot token is required so that Rasa can verify that CVG is communicating with your Rasa Bot.

The optional `blocking_endpoints` option allows to disable blocking CVG's request while processing the user message.
For compatibility reasons this option defaults to `true`, but we recommend setting it to `false`.

### Configuring CVG

If you do not yet have an account for CVG please contact us at [info@vier.ai](mailto:info@vier.ai).

![conversational-ai-rasa](https://user-images.githubusercontent.com/42033366/192627897-cc2ec42e-0bf4-4c91-bcf9-242a6077b609.PNG)

To configure the connection between your Rasa bot and [CVG](https://cognitivevoice.io) just select Rasa as the bot template, enter your Rasa URL (e.g. `https://rasa.example.org/webhooks/vier-cvg`) and your token, as set in credentials.yaml, in the CVG project settings.

![Configuring a Rasa project in CVG](https://github.com/VIER-CognitiveVoice/rasa-vier-cvg/blob/master/CVG-UI-configuring-a-rasa-project.png)

### Using the VIER CVG Channel in Rasa

#### Recieving Messages from CVG (Events)

Every message and intent sent by CVG will have a metadata-field called `cvg_body`. This field will always contain the JSON sent by CVG to the Rasa channel.
In the following sections, the term "metadata" will refer to this `cvg_body` field.

Normal spoken inputs from the user as well as DTMF inputs will be transmitted as text inputs to Rasa. All other CVG events will trigger specific intents as described below.
All messages and intents will have CVG's dialog ID as the `sender_id` field.

Text inputs follow [this specification](/specs/?urls.primaryName=Bot%20API%20%28Client%29#/bot/message). An example for the text input metadata would be:

```json
{
  "dialogId": "09e59647-5c77-4c02-a1c5-7fb2b47060f1",
  "projectContext": {
    "projectToken": "d30b1c38-b2fd-39c8-bec2-b268871338b0",
    "resellerToken": "ed4aff6d-c6f8-4ac9-ab67-d072ef45d9a0"
  },
  "timestamp": 1535546718115,
  "type": "SPEECH",
  "text": "Hello!",
  "confidence": 100,
  "vendor": "GOOGLE",
  "language": "en-US",
  "callback": "https://cognitivevoice.io/v1"
}
```

Voice and DTMF inputs can be differentiated using the `type` field, which would be `SPEECH` for voice and `DTMF` for DTMF tones.


Here is a list of the intents triggered by CVG for certain events:

* `cvg_session`: This intent is triggered once (after a new call has been established) before anything else to allow the bot to respond e.g. with a greeting. Metadata is defined by [this specification](/specs/?urls.primaryName=Bot%20API%20%28Client%29#/bot/session)
* `cvg_terminated`: This intent is triggered once the conversation has been terminated by the user. Metadata is specified [here](/specs/?urls.primaryName=Bot%20API%20%28Client%29#/bot/terminated).
* `cvg_inactivity`: This intent is triggered once the inactivity timeout has been triggered due to a lack of user input. Metadata is specified [here](/specs/?urls.primaryName=Bot%20API%20%28Client%29#/bot/inactivity).
* `cvg_recording`: This intent is triggered once the recording status changes. Metadata is specified [here](/specs/?urls.primaryName=Bot%20API%20%28Client%29#/bot/answer).
* `cvg_answer_number`, `cvg_answer_multiplechoice` and `cvg_answer_timeout`: These intents are triggered once a prompt (see next section) of type `Number` or `MultipleChoice` complete are timeout. Metadata is specified [here](/specs/?urls.primaryName=Bot%20API%20%28Client%29#/bot/answer).
* `cvg_outbound_success`: The success result of `forward` or `bridge` (see next section). It signals that the outgoing call has been successfully established. Metadata is specified by the response objects of the matching operations from the [Call API](/specs/?urls.primaryName=Call%20API#/call/forward).
* `cvg_outbound_failure`: The failure result of `forward` or `bridge` (see next section). It signals that the outgoing call could not be established and provides some details as to why. Metadata is specified by the response objects of the matching operations from the [Call API](/specs/?urls.primaryName=Call%20API#/call/forward).
  Depending on the exact reason (check out the `OutboundCallFailure` model in the
  [API specification](/specs/?urls.primaryName=Call%20API) for all possible reasons) there might not
  be a `ringStartTimestamp` and the `ringTime` could be zero.


#### Sending Messages to CVG (Commands)

The output channel for CVG supports `text_message`s and `custom_json`.

Text messages will be translated into [Say](/specs/?urls.primaryName=Call%20API#/call/say)-commands.

Every other command supported by the channel must be triggered by using custom JSON. The key for the custom JSON messages is an encoding of CVG's API endpoints and follows this schema:

```
cvg_<path with underscores instead of slashes>
```

So for example in order to use the [/call/play](/specs/?urls.primaryName=Call%20API#/call/play) endpoint you would use `cvg_call_play` as the key, for [/call/transcription/switch](/specs/?urls.primaryName=Call%20API#/call/switchTranscription) it would be `cvg_call_transcription_switch` and so on.

The JSON values will be used as-is as the request-body for the API call, so refer to the API documentations, most commonly the [Call API](/specs/?urls.primaryName=Call%20API) for specifics.
The only exception to this is, that the dialog ID (`sender_id`) which is automatically injected into the payloads as necessary.

Currently all operation documented in the [Call API](/specs/?urls.primaryName=Call%20API) as well as dialog_delete and dialog_data are implemented.

In case you want to call an API endpoint which is a bit more complex like `/call/forward` or something that is currently not implemented in this channel, you can use simply make the request manually using python.

#### Build a Rasa Bot (Example)

After setting up your Rasa Installation and configuring the CVG Project, let's create a simple Rasa Bot together.  
Create a new folder and generate the default bot:
```
rasa init
```
The bot is ready to be tested. Make sure you expose it in a way CVG can reach it, and configure the CVG channel.  

You can start the Rasa bot using `rasa run`. Make sure, you run `rasa train` after modifying the bot.

Please paste the following intents into your `domain.yml`. See below, on how the intent section should look like. They are explained [above](#communication), but don't worry about that yet.
```
intents:
  - greet
  - goodbye
  - affirm
  - deny
  - mood_great
  - mood_unhappy
  - bot_challenge

  - cvg_outbound_success
  - cvg_outbound_failure
  - cvg_session
  - cvg_answer_multiplechoice # you can remove cvg_answer_*, if you don't use the /call/prompt feature.
  - cvg_answer_number
  - cvg_answer_timeout
  - cvg_message
  - cvg_inactivity
  - cvg_terminated
  - cvg_recording
```


To end the call / hang up after it said "Bye", you can modify the `utter_goodbye` message in the `domain.yml` like this:  
```
  utter_goodbye:
  - text: "Bye"
    custom:
      cvg_call_drop:
```

To forward the caller to an agent, you can modify `utter_iamabot` like this:
```
  utter_iamabot:
  - text: "I am a bot, powered by Rasa. But I will gladly forward you to a human."
    custom:
      cvg_call_forward:
        destinationNumber: "+4969907362380"
```


#### Use an action, to extract information from cvg

Please reference the Rasa documentation, on how to create and call a custom action.
This example will use the default Rasa action server, which you can start with `rasa run actions`

```
class ActionPrintCvgBody(Action):

    def name(self) -> Text:
        return "action_print_cvg_body" # The action name which you can use in your domain.yml

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
          cvg_body = None
          for e in tracker.events[::-1]: # The loop will find the last message from the user
            if e["event"] == "user":
              cvg_body = e["metadata"]["cvg_body"]
              break
          print("Found cvg_body: ", cvg_body) # After we found the last message from the user and stored the CVG response body in cvg_body, we can print it
        except KeyError as e:
          print("Failed to read cvg_body: ", e) # The last user message did not contain the cvg_body. 
          # Note: The cvg_body is added by the CVG channel and won't be available if you use a different channel
        finally:
          return []
```


#### Now that we can send requests to CVG, let's receive them
You may already notice that the bot immediately says something after calling. That is because we haven't told Rasa yet how to handle the `cvg_session` intent.  
That intent is triggered when [/session](https://stage.cognitivevoice.io/specs/?urls.primaryName=Bot%20API%20(Client)#/bot/session) in the [Bot API](https://stage.cognitivevoice.io/specs/?urls.primaryName=Bot%20API%20(Client)) is called.

In your `stories.yml` replace the intent `greet` with `cvg_session`:
```diff
  steps:
-   - intent: greet
+   - or:
+    - intent: greet
+    - intent: cvg_session
```
Make sure to do that with all 3 stories and run `rasa train` before starting the Rasa bot.

To extract more information from the message inside an action, please read about [Events](#from-cvg-to-rasa-events) above.

The intents `cvg_outbound_success` and `cvg_outbound_failure` are relevant if you want to forward or bridge a call.  
You could do something like this in your `domain.yml`:
```
  utter_outbound_failure:
  - text: "Unfortunatly, the outbound call failed."
```
and in your `rules.yml`:
```
- rule: Handle outbound call failure
  steps:
  - intent: cvg_outbound_failure
  - action: utter_outbound_failure
```

This will inform the user about outbound call failures.
To handle the `cvg_outbound_success` intent, you can create an action, but we cannot say something to a call that has already been forwarded.

#### Prompt 
If you want to use the `/call/prompt` feature to prompt for a number, you can create the prompt and responses in your `domain.yml`:
```
  utter_prompt:
    - custom:
      cvg_call_prompt:
        text: Please provide 3 Numbers
        timeout: 10000
        type: 
          name: Number
          maxDigits: 3
          submitInputs:
            - DTMF_#

  utter_prompt_answer_number:
  - text: "You can access the result of the prompt inside a custom action."

  utter_prompt_timeout:
  - text: "You did not provide an answer, the prompt timed out"
```
For how the write such an action, see [below](#use-an-action-to-extract-information-from-cvg).

And add the following rules inside your `data/rules.yml`:
```
- rule: Handle prompt timeout
  steps:
  - intent: cvg_answer_timeout
  - action: utter_prompt_timeout

- rule: Handle prompt answer
  steps:
  - intent: cvg_answer_number
  - action: utter_prompt_answer_number
```


### Demo Voicebot built with Rasa and CVG

We provide a demo voicebot built with Rasa and CVG on [GitHub](https://github.com/VIER-CognitiveVoice/rasa-meter-reading-bot/). We also run this voicebot, so you can simply get a first impression. For more information, visit our [GitHub project](https://github.com/VIER-CognitiveVoice/rasa-meter-reading-bot/).

### Some details about the structure of this channel
- When CVG sends an event to Rasa, this channel will generate the intent (as specified [above](#from-rasa-to-cvg-commands))
  - The intent's metadata will contain the body sent by CVG as specified in the [Bot API](https://stage.cognitivevoice.io/specs/?urls.primaryName=Bot%20API%20(Client))
- When you utter a text message, or a [Custom Response](https://rasa.com/docs/rasa/responses/#custom-output-payloads), we pass the content of the payload to CVG after adding the `dialog_id`