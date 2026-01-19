"""
CLI (Command Line Interface) for Webhook Tunnel
"""
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .manager import TunnelManager

console = Console()


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    Webhook Tunnel - Expose local ports with custom DNS
        
    Use 'tunnel-tui' for an interactive interface.
    """
    pass


@cli.command()
@click.argument('name')
@click.argument('local_port', type=int)
@click.option('--subdomain', '-s', help='Custom subdomain')
@click.option('--public-port', '-p', type=int, help='Custom public port')
@click.option(
    '--public/--no-public',
    'public_enabled',
    default=False,
    help='Expose tunnel to the internet (always uses localtunnel via npx/npm).',
)
def start(name, local_port, subdomain, public_port, public_enabled):
    """
    Start a new tunnel
    
    Example: tunnel start myapi 3000 --subdomain api
    """
    manager = TunnelManager()
    
    try:
        console.print(f"🚀 Starting tunnel '[cyan]{name}[/cyan]'...", style="bold")
        tunnel = manager.create_tunnel(
            name,
            local_port,
            subdomain,
            public_port,
            'localtunnel' if public_enabled else None,
        )

        external = tunnel.get('public_url_external')
        external_block = (
            f"\n[bold magenta]External URL:[/bold magenta] {external}\n"
            if external
            else ""
        )
        
        panel = Panel.fit(
            f"""[green]✅ Tunnel created successfully![/green]

[bold]Name:[/bold] {tunnel['name']}
[bold]Local Port:[/bold] {tunnel['local_port']}
[bold]Public Port:[/bold] {tunnel['public_port']}
[bold]Subdomain:[/bold] {tunnel['subdomain']}.{tunnel['domain']}

[bold cyan]Hostname URL:[/bold cyan] {tunnel['public_url']}
[bold cyan]Local URL (always works):[/bold cyan] {tunnel.get('local_url', '')}{external_block}

[dim]If your hostname doesn't resolve, you can test without OS DNS changes:[/dim]
[dim]{tunnel.get('curl_resolve_example', '')}[/dim]

[dim]Test external reachability (replace URL if needed):[/dim]
[dim]curl -v {tunnel.get('public_url_external','<external_url>')}/readyz[/dim]

[dim]💡 Use 'tunnel stop {name}' to stop the tunnel[/dim]
[dim]💡 Use 'tunnel-tui' for interactive interface[/dim]""",
            title="🚇 Tunnel Created",
            border_style="green"
        )
        console.print(panel)
        
    except ValueError as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('name')
def stop(name):
    """
    Stop an existing tunnel
    
    Example: tunnel stop myapi
    """
    manager = TunnelManager()
    
    try:
        console.print(f"🛑 Stopping tunnel '[cyan]{name}[/cyan]'...")
        manager.stop_tunnel(name)
        console.print(f"[green]✅ Tunnel '[cyan]{name}[/cyan]' stopped successfully![/green]")
    except ValueError as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('name')
def restart(name):
    """
    Restart an existing tunnel
    
    Example: tunnel restart myapi
    """
    manager = TunnelManager()
    
    try:
        console.print(f"🔄 Restarting tunnel '[cyan]{name}[/cyan]'...")
        tunnel = manager.restart_tunnel(name)
        console.print(f"[green]✅ Tunnel '[cyan]{name}[/cyan]' restarted![/green]")
        console.print(f"[cyan]Public URL:[/cyan] {tunnel['public_url']}")
    except ValueError as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        sys.exit(1)


@cli.command('list')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def list_tunnels(output_json):
    """List all active tunnels"""
    manager = TunnelManager()
    
    # Clean up dead tunnels
    dead = manager.cleanup_dead_tunnels()
    if dead:
        console.print(f"🧹 Removed {len(dead)} inactive tunnel(s)\n")
    
    tunnels = manager.list_tunnels()
    
    if not tunnels:
        console.print("[yellow]📭 No active tunnels[/yellow]")
        return
    
    if output_json:
        import json
        console.print_json(data=tunnels)
        return
    
    # Build table
    table = Table(title="🚇 Active Tunnels", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Local", justify="right")
    table.add_column("Public", justify="right")
    table.add_column("Local URL", style="blue")
    table.add_column("Provider", style="magenta")
    table.add_column("External URL", style="magenta")
    table.add_column("CPU%", justify="right")
    table.add_column("Memory", justify="right")
    
    for name, tunnel in tunnels.items():
        status_emoji = "🟢" if tunnel['status'] == 'running' else "🔴"
        status = f"{status_emoji} {tunnel['status']}"
        
        process_info = tunnel.get('process_info', {})
        cpu = f"{process_info.get('cpu_percent', 0):.1f}%"
        memory = f"{process_info.get('memory_mb', 0):.1f}MB"
        
        table.add_row(
            name,
            status,
            f":{tunnel['local_port']}",
            f":{tunnel['public_port']}",
            tunnel.get('public_url', ''),
            tunnel.get('public_provider', '') or "",
            tunnel.get('public_url_external', '') or "",
            cpu,
            memory
        )
    
    console.print(table)
    
    # Display statistics
    stats = manager.get_stats()
    console.print(f"\n[dim]Total: {stats['total_tunnels']} | "
                 f"Active: {stats['active_tunnels']} | "
                 f"CPU: {stats['total_cpu_percent']}% | "
                 f"Memory: {stats['total_memory_mb']:.1f}MB[/dim]")


@cli.command()
def cleanup():
    """Remove all inactive tunnels"""
    manager = TunnelManager()
    dead = manager.cleanup_dead_tunnels()
    
    if dead:
        console.print(f"[green]✅ Removed {len(dead)} inactive tunnel(s)[/green]")
        for name in dead:
            console.print(f"  • {name}")
    else:
        console.print("[green]✨ No inactive tunnels found[/green]")


@cli.command()
def stopall():
    """Stop all active tunnels"""
    manager = TunnelManager()
    tunnels = list(manager.list_tunnels().keys())
    
    if not tunnels:
        console.print("[yellow]📭 No active tunnels[/yellow]")
        return
    
    console.print(f"🛑 Stopping {len(tunnels)} tunnel(s)...")
    
    for name in tunnels:
        try:
            manager.stop_tunnel(name)
            console.print(f"  [green]✅[/green] {name}")
        except Exception as e:
            console.print(f"  [red]❌[/red] {name}: {e}")
    
    console.print("\n[green]✅ All tunnels stopped![/green]")


@cli.command()
@click.option('--domain', '-d', help='Base domain (e.g., localhost)')
def config(domain):
    """Configure global options"""
    manager = TunnelManager()
    
    if domain:
        manager.config['domain'] = domain
        manager.save_config()
        console.print(f"[green]✅ Domain configured:[/green] {domain}")
    else:
        console.print("[bold]⚙️  Current Configuration:[/bold]\n")
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in manager.config.items():
            table.add_row(key, str(value))
        
        console.print(table)


@cli.command()
@click.argument('name')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
def logs(name, lines, follow):
    """Show logs for a tunnel"""
    manager = TunnelManager()
    
    if name not in manager.tunnels:
        console.print(f"[red]❌ Tunnel '{name}' not found[/red]")
        sys.exit(1)
    
    console.print(f"[bold]📋 Logs for '[cyan]{name}[/cyan]':[/bold]")
    console.print("─" * 60)
    
    log_content = manager.get_logs(name, lines)
    
    if log_content.strip():
        syntax = Syntax(log_content, "log", theme="monokai", line_numbers=False)
        console.print(syntax)
    else:
        console.print("[dim](empty)[/dim]")
    
    if follow:
        console.print("\n[dim]Following logs (Ctrl+C to stop)...[/dim]")
        import time
        try:
            while True:
                time.sleep(1)
                new_content = manager.get_logs(name, 10)
                if new_content.strip():
                    console.print(new_content, end='')
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped following logs[/yellow]")


@cli.command()
@click.argument('name')
def info(name):
    """Show detailed information about a tunnel"""
    manager = TunnelManager()
    
    tunnel = manager.get_tunnel(name)
    
    if not tunnel:
        console.print(f"[red]❌ Tunnel '{name}' not found[/red]")
        sys.exit(1)
    
    # Process information
    process_info = tunnel.get('process_info', {})
    
    info_text = f"""[bold cyan]Tunnel Information[/bold cyan]

[bold]General:[/bold]
  Name: {tunnel['name']}
  Status: {"🟢 " + tunnel['status'] if tunnel['status'] == 'running' else "🔴 " + tunnel['status']}
  Created: {tunnel['created_at']}

[bold]Ports:[/bold]
  Local Port: {tunnel['local_port']}
  Public Port: {tunnel['public_port']}
  
[bold]Network:[/bold]
  Subdomain: {tunnel['subdomain']}.{tunnel['domain']}
  Public URL: {tunnel['public_url']}

[bold]Process:[/bold]
  PID: {tunnel.get('pid', 'N/A')}
  CPU: {process_info.get('cpu_percent', 0):.2f}%
  Memory: {process_info.get('memory_mb', 0):.2f} MB
"""
    
    panel = Panel(info_text, title=f"🚇 {name}", border_style="cyan")
    console.print(panel)


@cli.command()
def stats():
    """Show overall statistics"""
    manager = TunnelManager()
    stats = manager.get_stats()
    
    stats_text = f"""[bold cyan]Overall Statistics[/bold cyan]

[bold]Tunnels:[/bold]
  Total: {stats['total_tunnels']}
  Active: {stats['active_tunnels']}
  Dead: {stats['dead_tunnels']}

[bold]Resources:[/bold]
  Total CPU: {stats['total_cpu_percent']}%
  Total Memory: {stats['total_memory_mb']:.2f} MB
"""
    
    panel = Panel(stats_text, title="📊 Statistics", border_style="green")
    console.print(panel)


@cli.command()
def tui():
    """Launch interactive TUI interface"""
    console.print("[cyan]Launching TUI interface...[/cyan]")
    from .tui import main as tui_main
    tui_main()


def main():
    """Entry point for CLI"""
    cli()


if __name__ == '__main__':
    main()
