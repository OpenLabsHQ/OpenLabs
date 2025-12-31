from ....enums.providers import OpenLabsProvider
from .aws_provider import aws_provider
from .protocol import PulumiProvider

PROVIDER_REGISTRY: dict[OpenLabsProvider, PulumiProvider] = {
    OpenLabsProvider.AWS: aws_provider,
}
