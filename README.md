# Rasa and VIER Cognitive Voice Gateway

Rasa is the leading open-source conversational AI platform that enables both individual developers and large enterprises to build superior AI assistants and chatbots. Rasa provides the infrastructure and tools needed to build the outstanding tools and transform the way customers communicate with businesses. Rasa can be deeply customized down to levels not possible with other platforms due to the open sourced architecture and machine learning.

Rasa is used by millions of developers and small teams to program enterprise conversational AI applications.

[VIER Cognitive Voice Gateway (CVG)](https://cognitivevoice.io/docs) enables access to telephony, speech-to-text (STT), text-to-speech (TTS) and contact center integration for chatbots built with Rasa. I.e. CVG makes your chatbot to a voicebot handling phone calls.

### Installing VIER CVG Channel in Rasa

To build voicebots using Rasa and CVG use our VIER CVG channel provided in this package. It needs to be installed as part of your Rasa installation.

#### Installing Rasa

If you do not have installed Rasa yet, follow the [installation guide](https://rasa.com/docs/rasa/installation/installing-rasa-open-source) as provided by Rasa.

#### Installing VIER CVG Channel for Rasa

The VIER CVG channel in Rasa implements all the CVG APIs relevant for bots to provide CVGs full power to you as a Rasa developer. 

The easiest way to install this package is through PyPI.

```
pip install rasa-vier-cvg
```

#### Docker

If you are using Rasa on Docker and you don't want to build a derived image, you can also download the [channel source](https://github.com/VIER-CognitiveVoice/rasa-vier-cvg/) and bind-mount the package into a `rasa/rasa`-base container with a volume definition like this:

```
./rasa_vier_cvg:/opt/venv/lib/python3.10/site-packages/rasa_vier_cvg
```

### Configure Rasa

Add the following content to `credentials.yml`:

```
rasa_vier_cvg.CVGInput:
  token: "CHOOSE_YOUR_TOKEN"
```

### Configuring CVG

If you do not yet have an account for CVG please contact us at [info@vier.ai](mailto:info@vier.ai).

![conversational-ai-rasa](https://user-images.githubusercontent.com/42033366/192627897-cc2ec42e-0bf4-4c91-bcf9-242a6077b609.PNG)

To configure the connection between your Rasa bot and [CVG](https://cognitivevoice.io) just select Rasa as the bot template, enter your Rasa URL (e.g. `https://rasa.example.org/webhooks/vier-cvg`) and your token, as set in credentials.yaml, in the CVG project settings.

![Configuring a Rasa project in CVG](https://github.com/VIER-CognitiveVoice/rasa-vier-cvg/blob/master/CVG-UI-configuring-a-rasa-project.png)

### Using the VIER CVG Channel in Rasa

The following APIs are part of the outgoing channel (from a bot perspective): [Call API](https://cognitivevoice.io/specs/?urls.primaryName=Call%20API), [Dialog API](https://cognitivevoice.io/specs/?urls.primaryName=Dialog%20API), [Assist API](https://cognitivevoice.io/specs/?urls.primaryName=Assist%20API), [Health API](https://cognitivevoice.io/specs/?urls.primaryName=Health%20API), [Recording API](https://cognitivevoice.io/specs/?urls.primaryName=Recording%20API).

The [Bot API](https://cognitivevoice.io/specs/?urls.primaryName=Bot%20API%20(Client)) is part the incoming channel (from a bot perspective). 

### More Information

See and try our [little sample voicebot](https://github.com/VIER-CognitiveVoice/rasa-meter-reading-bot) built with CVG and Rasa to go into more details.

Find more information on our Rasa integration and how to build voicebots with Rasa and CVG in our [docs](https://cognitivevoice.io/docs/conversational-ai/conversational-ai-rasa.html).
