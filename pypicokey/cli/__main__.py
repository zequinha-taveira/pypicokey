import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional
from pathlib import Path

from pypicokey import PicoKeyManager, DeviceMode
from pypicokey.provisioning import DeviceProvisioner, ProvisioningConfig

app = typer.Typer(help="pypicokey CLI - Management tool for PicoKey devices")
console = Console()

@app.command(name="list")
def list_devices():
    """List all connected PicoKey devices."""
    manager = PicoKeyManager()
    devices = manager.discover()
    
    if not devices:
        rprint("[yellow]No PicoKey devices found.[/yellow]")
        return
    
    table = Table(title="Connected PicoKey Devices")
    table.add_column("#", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Mode", style="magenta")
    table.add_column("Serial", style="yellow")
    table.add_column("Path", style="dim")
    
    for i, dev in enumerate(devices, 1):
        table.add_row(
            str(i),
            dev.name,
            str(dev.mode),
            dev.serial_number or "N/A",
            dev.info.path or "N/A"
        )
    
    console.print(table)

@app.command()
def info(
    index: int = typer.Option(1, help="Index of the device to inspect"),
    mode: Optional[str] = typer.Option(None, help="Filter by mode")
):
    """Show detailed information about a device."""
    manager = PicoKeyManager()
    mode_filter = None
    if mode:
        try:
            mode_filter = DeviceMode(mode.lower())
        except ValueError:
            valid = ", ".join(m.value for m in DeviceMode)
            rprint(f"[red]Error: Invalid mode '{mode}'. Valid modes: {valid}[/red]")
            return
    devices = manager.discover(mode_filter=mode_filter)
    
    if index > len(devices) or index < 1:
        rprint(f"[red]Error: Device index {index} out of range.[/red]")
        return
    
    device = devices[index - 1]
    rprint(f"\n[bold green]Device Information: {device.name}[/bold green]")
    rprint("-" * 40)
    rprint(f"  [bold]Mode:[/bold]       {device.mode}")
    rprint(f"  [bold]Serial:[/bold]     {device.serial_number or 'N/A'}")
    rprint(f"  [bold]Path:[/bold]       {device.info.path}")
    rprint(f"  [bold]Transport:[/bold]  {device.info.transport_type}")
    
    if "atr" in device.info.extra:
        rprint(f"  [bold]ATR:[/bold]        {device.info.extra['atr']}")

@app.command()
def provision(
    index: int = typer.Option(1, help="Index of the device to provision"),
    label: str = typer.Option("PicoKey", help="Label for the device"),
    user_pin: str = typer.Option(..., prompt=True, hide_input=True, help="Set user PIN"),
    admin_pin: str = typer.Option(..., prompt=True, hide_input=True, help="Set admin PIN"),
    reset: bool = typer.Option(False, help="Reset device before provisioning")
):
    """Provision a new PicoKey device."""
    manager = PicoKeyManager()
    devices = manager.discover()
    
    if index > len(devices) or index < 1:
        rprint(f"[red]Error: Device index {index} out of range.[/red]")
        return
        
    device = devices[index - 1]
    rprint(f"Provisioning [bold]{device.name}[/bold]...")
    
    config = ProvisioningConfig(
        device_label=label,
        user_pin=user_pin,
        admin_pin=admin_pin,
        reset_existing=reset
    )
    
    with device:
        provisioner = DeviceProvisioner(device)
        result = provisioner.provision(config)
        
        if result.success:
            rprint("[bold green]Success![/bold green] Device provisioned.")
        else:
            rprint(f"[bold red]Failed:[/bold red] {', '.join(result.errors)}")

@app.command()
def flash(
    index: int = typer.Option(1, help="Index of the device to flash"),
    file: Path = typer.Argument(..., help="Path to the UF2 firmware file")
):
    """Flash firmware to a device in Boot mode."""
    manager = PicoKeyManager()
    devices = manager.discover(mode_filter=DeviceMode.BOOT)
    
    if not devices:
        rprint("[yellow]No Pico devices in BOOT mode found.[/yellow]")
        rprint("Please connect your device while holding the BOOTSEL button.")
        return
        
    if index > len(devices) or index < 1:
        rprint(f"[red]Error: Device index {index} out of range.[/red]")
        return
        
    device = devices[index - 1]
    rprint(f"Flashing [bold]{device.name}[/bold] with [blue]{file.name}[/blue]...")
    
    from pypicokey.modules.boot import BootModule
    
    def progress_bar(current, total):
        rprint(f"  Progress: [green]{current}%[/green]", end="\r")
        if current == total: rprint("")

    with device:
        boot = BootModule(device)
        try:
            success = boot.flash_firmware(file, progress_callback=progress_bar)
            if success:
                rprint("[bold green]Success![/bold green] Firmware flashed. The device will reboot.")
            else:
                rprint("[bold red]Failed:[/bold red] Flashing verification failed.")
        except Exception as e:
            rprint(f"[bold red]Error:[/bold red] {e}")


# HSM Subcommands
hsm_app = typer.Typer(help="HSM management commands")
app.add_typer(hsm_app, name="hsm")

@hsm_app.command("list-keys")
def hsm_list_keys(index: int = typer.Option(1, help="Index of the HSM device")):
    """List keys on the HSM device."""
    manager = PicoKeyManager()
    devices = manager.discover(mode_filter=DeviceMode.HSM)
    
    if not devices:
        rprint("[yellow]No HSM devices found.[/yellow]")
        return

    if index > len(devices) or index < 1:
        rprint(f"[red]Error: Device index {index} out of range.[/red]")
        return

    device = devices[index - 1]
    from pypicokey.modules.hsm import HSMModule

    with device:
        hsm = HSMModule(device)
        keys = hsm.list_keys()
        
        if not keys:
            rprint("No keys found on device.")
            return
            
        table = Table(title=f"Keys on {device.name}")
        table.add_column("Slot", style="cyan")
        table.add_column("Label", style="green")
        table.add_column("Type", style="magenta")
        table.add_column("Size", style="yellow")
        
        for k in keys:
            table.add_row(str(k.slot), k.label, k.key_type, str(k.key_size))
        
        console.print(table)

@hsm_app.command("generate-key")
def hsm_gen_key(
    index: int = typer.Option(1, help="Index of the HSM device"),
    label: str = typer.Option(..., help="Label for the new key"),
    type: str = typer.Option("rsa", help="Key type (rsa, ec)")
):
    """Generate a new key pair on the HSM."""
    manager = PicoKeyManager()
    devices = manager.discover(mode_filter=DeviceMode.HSM)
    
    if not devices:
        rprint("[yellow]No HSM devices found.[/yellow]")
        return

    if index > len(devices) or index < 1:
        rprint(f"[red]Error: Device index {index} out of range.[/red]")
        return

    device = devices[index - 1]
    from pypicokey.modules.hsm import HSMModule

    with device:
        hsm = HSMModule(device)
        rprint(f"Generating {type.upper()} key '[bold]{label}[/bold]'...")
        key = hsm.generate_key(label, key_type=type.upper())
        rprint(f"[bold green]Success![/bold green] Key generated in slot {key.slot}.")

if __name__ == "__main__":
    app()
