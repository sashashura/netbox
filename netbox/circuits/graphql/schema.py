from .types import *

# schema.py
import strawberry
from typing import List


@strawberry.type
class CircuitsQuery:
    circuit: CircuitType = strawberry.django.field()
    circuit_list: List[CircuitType] = strawberry.django.field()

    circuit_termination: CircuitTerminationType = strawberry.django.field()
    circuit_termination_list: List[CircuitTerminationType] = strawberry.django.field()

    circuit_type: CircuitTypeType = strawberry.django.field()
    circuit_type_list: List[CircuitTypeType] = strawberry.django.field()

    provider: ProviderType = strawberry.django.field()
    provider_list: List[ProviderType] = strawberry.django.field()

    provider_network: ProviderNetworkType = strawberry.django.field()
    provider_network_list: List[ProviderNetworkType] = strawberry.django.field()
