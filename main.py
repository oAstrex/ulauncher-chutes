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
        endpoint = "https://llm.chutes.ai/v1/chat/completions"

        logger.info('Processing user preferences')
        try:
            api_key = extension.preferences['api_key']
            model = extension.preferences['model']
            system_prompt = extension.preferences['system_prompt']
            line_wrap = int(extension.preferences['line_wrap'])
        except Exception as err:
            logger.error('Failed to parse preferences: %s', str(err))
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse preferences: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        search_term = event.get_argument()
        logger.info('The search term is: %s', search_term)
        if not search_term:
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Type in a prompt...',
                                    on_enter=DoNothingAction())
            ])

        headers = {
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json'
        }

        data = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": search_term}
            ]
        })

        try:
            response = requests.post(endpoint, headers=headers, data=data, timeout=10)
        except Exception as err:
            logger.error('Request failed: %s', str(err))
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Request failed: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        try:
            response = response.json()
            choices = response['choices']
        except Exception as err:
            logger.error('Failed to parse response: %s', str(response))
            errMsg = "Unknown error, please check logs for more info"
            try:
                errMsg = response['error']['message']
            except Exception:
                pass

            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse response: ' + errMsg,
                                    on_enter=CopyToClipboardAction(str(errMsg)))
            ])

        items = []
        try:
            for choice in choices:
                message = choice['message']['content']
                message = wrap_text(message, line_wrap)

                items.append(ExtensionResultItem(icon=EXTENSION_ICON, name="Chutes AI", description=message,
                                                 on_enter=CopyToClipboardAction(message)))
        except Exception as err:
            logger.error('Failed to parse choices: %s', str(response))
            return RenderResultListAction([
                ExtensionResultItem(icon=EXTENSION_ICON,
                                    name='Failed to parse choices: ' + str(err),
                                    on_enter=CopyToClipboardAction(str(err)))
            ])

        return RenderResultListAction(items)


if __name__ == '__main__':
    AskExtension().run()
