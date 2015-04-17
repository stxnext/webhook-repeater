# WebHook Repeater

WebHook Repeater is small web application that receives http requests and forwards them to remote endpoints (you can configure what is forwarded where). If endpoint is temporary incapable to accept requests, Repeater stores them in Redis database and tries to deliver later.
