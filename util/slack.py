from slack_sdk.webhook import WebhookClient
import yaml
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(script_dir, "..", "configs", "env.yml")
config = yaml.safe_load(open(config_path, "r"))


def send_slack_message(message):
    url = config["slack"]["webhook_url"]
    webhook = WebhookClient(url)
    webhook.send(text=message)
