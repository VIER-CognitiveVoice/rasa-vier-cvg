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

### Configure Rasa

Add the following content to `credentials.yml`:

```
rasa_vier_cvg.CVGInput:
  token: "CHOOSE_YOUR_TOKEN"
```

### Configuring CVG

![conversational-ai-rasa](https://user-images.githubusercontent.com/42033366/192627897-cc2ec42e-0bf4-4c91-bcf9-242a6077b609.PNG)

To configure the connection between your Rasa bot and [CVG](https://cognitivevoice.io) just select Rasa as the bot template, enter your Rasa URL (something like "https://myrasabot.mycompany.ai/webhooks/vier-cvg") and your token as set in credentials.aml in the CVG project settings. That's it.

### Using the VIER CVG Channel in Rasa

The following APIs are part of the outgoing channel (from a bot perspective): [Call API](https://cognitivevoice.io/specs/?urls.primaryName=Call%20API), [Dialog API](https://cognitivevoice.io/specs/?urls.primaryName=Dialog%20API), [Assist API](https://cognitivevoice.io/specs/?urls.primaryName=Assist%20API), [Health API](https://cognitivevoice.io/specs/?urls.primaryName=Health%20API), [Recording API](https://cognitivevoice.io/specs/?urls.primaryName=Recording%20API).

The [Bot API](https://cognitivevoice.io/specs/?urls.primaryName=Bot%20API%20(Client)) is part the incoming channel (from a bot perspective). 

### More Information

Find more information on our Rasa integration and how to build voicebots with Rasa and CVG in our [docs](https://cognitivevoice.io/docs/conversational-ai/conversational-ai-rasa.html).
