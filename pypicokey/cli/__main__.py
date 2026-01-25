import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional

from pypicokey import PicoKeyManager, DeviceMode
from pypicokey.provisioning import DeviceProvisioner, ProvisioningConfig

app = typer.Typer(help="pypicokey CLI - Management tool for PicoKey devices")
console = Console()

@app.command()
def list():
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
    mode_filter = DeviceMode(mode.lower()) if mode else None
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

if __name__ == "__main__":
    app()
