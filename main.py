import logging
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
import requests
import json

logger = logging.getLogger(__name__)
EXTENSION_ICON = 'images/icon.png'

def wrap_text(text, max_w):
    logger.debug(f"Wrapping text to max width {max_w}")
    words = text.split()
    lines = []
    current_line = ''
    for word in words:
        if len(current_line + word) <= max_w:
            current_line += ' ' + word
        else:
            lines.append(current_line.strip())
            current_line = word
    lines.append(current_line.strip())
    logger.debug(f"Wrapped text: {lines}")
    return '\n'.join(lines)

class AskExtension(Extension):
    """
    Ulauncher extension to generate text using Chutes AI
    """
    def __init__(self):
        super(AskExtension, self).__init__()
        logger.info('Chutes AI Ask extension started')
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())

class KeywordQueryEventListener(EventListener):
    """
    Event listener for KeywordQueryEvent
    """

    def on_event(self, event, extension):
        logger.debug("Entered on_event handler.")
        endpoint = "https://llm.chutes.ai/v1/chat/completions"

        logger.info('Processing user preferences')
        try:
            api_key = extension.preferences['api_key']
            max_tokens = int(extension.preferences['max_tokens'])
            model = extension.preferences['model']
            system_prompt = extension.preferences['system_prompt']
            line_wrap = int(extension.preferences['line_wrap'])
            logger.debug(f"Preferences - api_key: {api_key}, model: {model}, system_prompt: {system_prompt}, line_wrap: {line_wrap}")
        except Exception as err:
            logger.error('Failed to parse preferences: %s', str(err), exc_info=True)
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse preferences: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        search_term = event.get_argument()
        logger.info('The search term is: %s', search_term)
        if not search_term:
            logger.debug("No search term provided.")
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Type in a prompt...',
                                    on_enter=DoNothingAction())
            ])

        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + api_key
        }

        body = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": search_term
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model": model,
        }
        body = json.dumps(body)
        logger.debug(f"Request data: {data}")

        try:
            logger.debug(f"Sending POST request to {endpoint}")
            response = requests.post(endpoint, headers=headers, data=data, timeout=10)
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Raw response text: {response.text}")
        except Exception as err:
            logger.error('Request failed: %s', str(err), exc_info=True)
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Request failed: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        try:
            response_json = response.json()
            logger.debug(f"Response JSON: {response_json}")
            choices = response_json['choices']
        except Exception as err:
            logger.error('Failed to parse response: %s', str(response), exc_info=True)
            errMsg = "Unknown error, please check logs for more info"
            try:
                errMsg = response_json['error']['message']
            except Exception:
                logger.debug("No detailed error message found in response JSON.")
                pass

            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse response: ' + errMsg,
                                    on_enter=CopyToClipboardAction(str(errMsg)))
            ])

        items = []
        try:
            for idx, choice in enumerate(choices):
                logger.debug(f"Parsing choice {idx}: {choice}")
                message = choice['message']['content']
                message = wrap_text(message, line_wrap)

                items.append(ExtensionResultItem(icon=EXTENSION_ICON, name="Chutes AI", description=message,
                                                 on_enter=CopyToClipboardAction(message)))
            logger.debug(f"Created {len(items)} ExtensionResultItems.")
        except Exception as err:
            logger.error('Failed to parse choices: %s', str(response_json), exc_info=True)
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse choices: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        logger.debug("Returning results to Ulauncher.")
        return RenderResultListAction(items)

if __name__ == '__main__':
    logger.debug("Starting AskExtension main entrypoint.")
    AskExtension().run()
