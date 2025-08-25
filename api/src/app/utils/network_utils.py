from ipaddress import IPv4Network
from typing import Generator


def _reverse_subnet_generator(
    supernet: IPv4Network, new_prefix: int
) -> Generator[IPv4Network, None, None]:
    """
    A memory-efficient generator that yields subnets of a given prefix length
    from a supernet, starting from the highest address and moving downwards.

    Args:
        supernet: The larger network to iterate through (e.g., 10.0.0.0/8).
        new_prefix: The prefix length for the subnets to be generated.

    Yields:
        IPv4Network objects in reverse order.
    """
    # Calculate the size of one subnet of the desired prefix length
    subnet_size = 1 << (32 - new_prefix)

    # Find the starting address of the very last possible subnet
    # This is done by taking the broadcast address of the supernet and aligning
    # it to the boundary of the new subnet size.
    last_subnet_start_int = int(supernet.broadcast_address) & -subnet_size
    current_addr = last_subnet_start_int

    # Iterate downwards as long as the current address is within the supernet
    while current_addr >= int(supernet.network_address):
        yield IPv4Network((current_addr, new_prefix))
        current_addr -= subnet_size


def find_available_network(
    existing_networks: list[IPv4Network],
    new_prefix: int,
    prefer_high_ranges: bool = False,
) -> IPv4Network:
    """
    Finds an available IPv4 network of a given prefix length that does not
    overlap with existing networks within private IP address ranges.

    Args:
        existing_networks: A list of IPv4Network objects.
        new_prefix: The desired prefix length for the new network (e.g., 24).
        prefer_high_ranges:
            If False (default): Searches from 10.0.0.0/8 upwards, iterating
            from the lowest subnet to the highest. Ideal for standard networks.
            If True: Prioritizes 172.16.0.0/12 and searches from the highest
            subnet downwards. Ideal for creating visually distinct networks
            for management or VPNs.

    Returns:
        An IPv4Network object for the first available network found.

    Raises:
        ValueError: If the new_prefix is invalid or if no available network
                    can be found.
    """
    # 1. Validate the desired new prefix length
    if not 0 <= new_prefix <= 32:
        raise ValueError("The 'new_prefix' must be between 0 and 32.")

    # 2. Define the search order and subnet iterator based on the flag
    if prefer_high_ranges:
        # Prioritize 172.16/12, then 192.168/16, then 10/8 for max visual distance
        private_ranges = [
            IPv4Network("172.16.0.0/12"),
            IPv4Network("192.168.0.0/16"),
            IPv4Network("10.0.0.0/8"),
        ]
        # Use the memory-efficient reverse generator
        get_subnet_iterator = _reverse_subnet_generator
    else:
        # Standard search order: 10/8, 172.16/12, 192.168/16
        private_ranges = [
            IPv4Network("10.0.0.0/8"),
            IPv4Network("172.16.0.0/12"),
            IPv4Network("192.168.0.0/16"),
        ]
        # Use the standard library's forward generator
        get_subnet_iterator = lambda net, prefix: net.subnets(new_prefix=prefix)

    # 3. Iterate through each private range to find an available subnet
    for private_range in private_ranges:
        # Skip this private range if the requested network is larger than the range itself
        if new_prefix < private_range.prefixlen:
            continue

        # Get the appropriate subnet iterator (forward or reverse)
        subnet_iterator = get_subnet_iterator(private_range, new_prefix)

        for subnet in subnet_iterator:
            # Assume the subnet is available until an overlap is found
            is_overlapping = False
            for existing_net in existing_networks:
                if subnet.overlaps(existing_net):
                    is_overlapping = True
                    break  # Found an overlap, no need to check other existing networks

            # If after checking all existing networks, no overlap was found, return this subnet
            if not is_overlapping:
                return subnet

    # 4. If the loops complete, no available network was found
    raise ValueError(f"No available /{new_prefix} network found in private IP ranges.")
