#!/usr/bin/env python3

import os
import sys
import json
import click
import socket
import subprocess
import signal
import time
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / '.webhook-tunnel'
CONFIG_FILE = CONFIG_DIR / 'config.json'
TUNNELS_FILE = CONFIG_DIR / 'tunnels.json'
LOG_DIR = CONFIG_DIR / 'logs'

class TunnelManager:
    
    def __init__(self):
        self.ensure_config_dir()
        self.config = self.load_config()
        self.tunnels = self.load_tunnels()
    
    def ensure_config_dir(self):
        CONFIG_DIR.mkdir(exist_ok=True)
        LOG_DIR.mkdir(exist_ok=True)
        
        if not CONFIG_FILE.exists():
            default_config = {
                'domain': 'localhost',
                'base_port': 8000,
                'nginx_enabled': False,
                'nginx_config_path': '/etc/nginx/sites-available',
            }
            self.save_json(CONFIG_FILE, default_config)
    
    def load_config(self):
        return self.load_json(CONFIG_FILE)
    
    def load_tunnels(self):
        if TUNNELS_FILE.exists():
            return self.load_json(TUNNELS_FILE)
        return {}
    
    def save_tunnels(self):
        self.save_json(TUNNELS_FILE, self.tunnels)
    
    @staticmethod
    def load_json(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def save_json(filepath, data):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def is_port_available(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0
    
    def create_tunnel(self, name, local_port, subdomain=None, public_port=None):
        if name in self.tunnels:
            raise ValueError(f"Tunnel '{name}' already exists")
        
        if self.is_port_available(local_port):
            raise ValueError(f"Local port {local_port} is not in use. Restart your service first")
        
        if not subdomain:
            subdomain = name
        
        if not public_port:
            public_port = self.find_available_port()
        
        domain = self.config.get('domain', 'localhost')
        public_url = f"http://{subdomain}.{domain}:{public_port}"
        
        tunnel_info = {
            'name': name,
            'local_port': local_port,
            'public_port': public_port,
            'subdomain': subdomain,
            'domain': domain,
            'public_url': public_url,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'pid': None
        }
        
        pid = self.start_proxy(tunnel_info)
        tunnel_info['pid'] = pid
        
        self.tunnels[name] = tunnel_info
        self.save_tunnels()
        
        return tunnel_info
    
    def find_available_port(self, start=8000, end=9000):
        for port in range(start, end):
            if self.is_port_available(port):
                if not any(t.get('public_port') == port for t in self.tunnels.values()):
                    return port
        raise RuntimeError("No avaliable local port found")
    
    def start_proxy(self, tunnel_info):
        local_port = tunnel_info['local_port']
        public_port = tunnel_info['public_port']
        name = tunnel_info['name']
        
        log_file = LOG_DIR / f"{name}.log"
        
        cmd = [
            'socat',
            f'TCP-LISTEN:{public_port},fork,reuseaddr',
            f'TCP:127.0.0.1:{local_port}'
        ]
        
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        time.sleep(0.5)
        
        if process.poll() is not None:
            raise RuntimeError(f"Failed to start proxy. Check log file: {log_file}")
        
        return process.pid
    
    def stop_tunnel(self, name):
        if name not in self.tunnels:
            raise ValueError(f"Tunnel '{name}' not found")
        
        tunnel = self.tunnels[name]
        pid = tunnel.get('pid')
        
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass
        
        del self.tunnels[name]
        self.save_tunnels()
    
    def list_tunnels(self):
        return self.tunnels
    
    def cleanup_dead_tunnels(self):
        dead_tunnels = []
        
        for name, tunnel in self.tunnels.items():
            pid = tunnel.get('pid')
            if pid:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    dead_tunnels.append(name)
        
        for name in dead_tunnels:
            del self.tunnels[name]
        
        if dead_tunnels:
            self.save_tunnels()
        
        return dead_tunnels


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    Webhook Tunnel - Exponha portas locais com DNS customizado
    
    Ferramenta para desenvolvedores testarem webhooks e callbacks facilmente.
    """
    pass


@cli.command()
@click.argument('name')
@click.argument('local_port', type=int)
@click.option('--subdomain', '-s', help='Custom subdomain')
@click.option('--public-port', '-p', type=int, help='Custom public port')
def start(name, local_port, subdomain, public_port):
    """
    Inicia um novo túnel
    
    Exemplo: tunnel start myapi 3000 --subdomain api
    """
    manager = TunnelManager()
    
    try:
        click.echo(f"🚀 Startting tunnel '{name}'...")
        tunnel = manager.create_tunnel(name, local_port, subdomain, public_port)
        
        click.echo(click.style("✅ Tunnel successfully created!", fg='green', bold=True))
        click.echo()
        click.echo(f"📍 Name: {tunnel['name']}")
        click.echo(f"🔗 Public URL: {click.style(tunnel['public_url'], fg='cyan', bold=True)}")
        click.echo(f"🏠 Local port: {tunnel['local_port']}")
        click.echo(f"🌐 Public port: {tunnel['public_port']}")
        click.echo(f"📝 Subdomain: {tunnel['subdomain']}.{tunnel['domain']}")
        click.echo()
        click.echo("💡 Use 'tunnel stop {}' to stop tunnel".format(name))
        
    except ValueError as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"❌ Unexpected error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
def stop(name):
    """
    Para um túnel existente
    
    Exemplo: tunnel stop myapi
    """
    manager = TunnelManager()
    
    try:
        click.echo(f"🛑 Stopping tunnel '{name}'...")
        manager.stop_tunnel(name)
        click.echo(click.style(f"✅ Tunnel '{name}' successfully stopped!", fg='green'))
    except ValueError as e:
        click.echo(click.style(f"❌ Erro: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command('list')
def list_tunnels():
    """Lista todos os túneis ativos"""
    manager = TunnelManager()
    
    # Limpa túneis mortos
    dead = manager.cleanup_dead_tunnels()
    if dead:
        click.echo(f"🧹 Removed {len(dead)} idle tunnels")
        click.echo()
    
    tunnels = manager.list_tunnels()
    
    if not tunnels:
        click.echo("📭 No idle tunnels found")
        return
    
    click.echo(click.style("🚇 Running tunnels:", fg='blue', bold=True))
    click.echo()
    
    for name, tunnel in tunnels.items():
        click.echo(f"  {click.style('●', fg='green')} {click.style(name, bold=True)}")
        click.echo(f"    URL: {click.style(tunnel['public_url'], fg='cyan')}")
        click.echo(f"    Local: localhost:{tunnel['local_port']} → Public: :{tunnel['public_port']}")
        click.echo(f"    PID: {tunnel.get('pid', 'N/A')}")
        click.echo()


@cli.command()
def cleanup():
    manager = TunnelManager()
    dead = manager.cleanup_dead_tunnels()
    
    if dead:
        click.echo(click.style(f"✅ Removed {len(dead)} idle tunnels", fg='green'))
        for name in dead:
            click.echo(f"  • {name}")
    else:
        click.echo("✨ No idle tunnel found")


@cli.command()
def stopall():
    """Para todos os túneis ativos"""
    manager = TunnelManager()
    tunnels = list(manager.list_tunnels().keys())
    
    if not tunnels:
        click.echo("📭 No running tunnels")
        return
    
    click.echo(f"🛑 Stopping {len(tunnels)} tunnels...")
    
    for name in tunnels:
        try:
            manager.stop_tunnel(name)
            click.echo(f"  ✅ {name}")
        except Exception as e:
            click.echo(f"  ❌ {name}: {e}")
    
    click.echo(click.style("\n✅ All tunels stopped!", fg='green'))


@cli.command()
@click.option('--domain', '-d', help='Base domain (ex: localhost)')
def config(domain):
    """Configura opções globais"""
    manager = TunnelManager()
    
    if domain:
        manager.config['domain'] = domain
        manager.save_json(CONFIG_FILE, manager.config)
        click.echo(click.style(f"✅ Domain set: {domain}", fg='green'))
    else:
        click.echo("⚙️  Current config:")
        click.echo()
        for key, value in manager.config.items():
            click.echo(f"  {key}: {value}")


@cli.command()
@click.argument('name')
def logs(name):
    """Mostra logs de um túnel"""
    manager = TunnelManager()
    
    if name not in manager.tunnels:
        click.echo(click.style(f"❌ Tunnel '{name}' not found", fg='red'), err=True)
        sys.exit(1)
    
    log_file = LOG_DIR / f"{name}.log"
    
    if not log_file.exists():
        click.echo(f"📭 No log avaliable for '{name}'")
        return
    
    click.echo(f"📋 Logs : '{name}':")
    click.echo("─" * 60)
    
    with open(log_file, 'r') as f:
        content = f.read()
        if content.strip():
            click.echo(content)
        else:
            click.echo("(empty)")


if __name__ == '__main__':
    cli()
