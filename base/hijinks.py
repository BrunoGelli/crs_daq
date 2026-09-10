"""Pure Rev5/Hijinks logical/physical UART definitions."""

RX_MASK_REGISTER = 0x201C
PACKET_DELAY_BASE = 0x03014
PACKET_DELAY_STRIDE = 0x1000
UART_CLOCK_BASE = 0x03010
UART_CLOCK_STRIDE = 0x1000
DEAD_LOGICAL_CHANNELS = frozenset(range(12, 41, 4))


def logical_to_physical_uart(logical_channel):
    logical_channel = int(logical_channel)
    if logical_channel < 1 or logical_channel > 40:
        raise ValueError(f"Logical IO channel must be in [1, 40], got {logical_channel}")
    if logical_channel in DEAD_LOGICAL_CHANNELS:
        raise ValueError(f"Hijinks logical IO channel {logical_channel} is dead")
    return logical_channel - max(0, (logical_channel - 9) // 4)


def physical_rx_mask(physical_uarts):
    mask = 0xFFFFFFFF
    for uart in physical_uarts:
        uart = int(uart)
        if uart < 1 or uart > 32:
            raise ValueError(f"Physical UART must be in [1, 32], got {uart}")
        mask &= ~(1 << (uart - 1))
    return mask


def physical_uart_clock_register(physical_uart):
    """Return the persistent clock-ratio register for a physical UART."""
    physical_uart = int(physical_uart)
    if physical_uart < 1 or physical_uart > 32:
        raise ValueError(f"Physical UART must be in [1, 32], got {physical_uart}")
    return UART_CLOCK_BASE + (physical_uart - 1) * UART_CLOCK_STRIDE
