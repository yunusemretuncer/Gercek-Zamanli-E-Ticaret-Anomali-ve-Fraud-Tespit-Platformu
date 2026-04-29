from fastapi import Request

from shared.messaging.publisher import RabbitMQPublisher

#For Dependency injection
def get_publisher(request: Request) -> RabbitMQPublisher:
    return request.app.state.publisher