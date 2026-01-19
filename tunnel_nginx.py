#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
from tunnel_cli import TunnelManager, click

class NginxTunnelManager(TunnelManager):
    
    def __init__(self):
        super().__init__()
        self.nginx_available = self.check_nginx()
    
    def check_nginx(self):
        try:
            subprocess.run(['nginx', '-v'], 
                         capture_output=True, 
                         check=True)
            return True
        except:
            return False
    
    def create_nginx_config(self, tunnel_info):
        if not self.nginx_available:
            return None
        
        subdomain = tunnel_info['subdomain']
        domain = tunnel_info['domain']
        public_port = tunnel_info['public_port']
        full_domain = f"{subdomain}.{domain}"
        
        config_content = f"""
# Automatic configuration for {tunnel_info['name']}
server {{
    listen 80;
    server_name {full_domain};

    access_log /var/log/nginx/{subdomain}-access.log;
    error_log /var/log/nginx/{subdomain}-error.log;

    location / {{
        proxy_pass http://127.0.0.1:{public_port};
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
}}
"""
        
        config_path = Path(f"/tmp/tunnel-{subdomain}.conf")
        config_path.write_text(config_content)
        
        return config_path
    
    def enable_nginx_site(self, config_path, name):
        try:
            dest = f"/etc/nginx/sites-available/tunnel-{name}"
            subprocess.run(['sudo', 'cp', str(config_path), dest], 
                         check=True)
            
            link = f"/etc/nginx/sites-enabled/tunnel-{name}"
            subprocess.run(['sudo', 'ln', '-sf', dest, link], 
                         check=True)
            
            subprocess.run(['sudo', 'nginx', '-t'], 
                         check=True)
            
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], 
                         check=True)
            
            return True
        except subprocess.CalledProcessError:
            return False
    
    def disable_nginx_site(self, name):
        try:
            link = f"/etc/nginx/sites-enabled/tunnel-{name}"
            subprocess.run(['sudo', 'rm', '-f', link], 
                         check=True)
            
            config = f"/etc/nginx/sites-available/tunnel-{name}"
            subprocess.run(['sudo', 'rm', '-f', config], 
                         check=True)
            
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], 
                         check=True)
            
            return True
        except subprocess.CalledProcessError:
            return False


@click.group()
def nginx_cli():
    pass


@nginx_cli.command()
@click.argument('name')
@click.argument('local_port', type=int)
@click.option('--subdomain', '-s', help='Subdomínio customizado')
@click.option('--nginx/--no-nginx', default=False, 
              help='Criar configuração nginx')
def create(name, local_port, subdomain, nginx):
    manager = NginxTunnelManager()
    
    try:
        click.echo(f"🚀 Creating tunnel '{name}'...")
        tunnel = manager.create_tunnel(name, local_port, subdomain)
        
        click.echo(click.style("✅ Tunnel created!", fg='green'))
        click.echo(f"🔗 URL: {tunnel['public_url']}")
        
        if nginx and manager.nginx_available:
            click.echo("\n📝 Creating nginx configuration...")
            config_path = manager.create_nginx_config(tunnel)
            
            if config_path:
                click.echo(f"✅ Nginx configurarion created: {config_path}")
                click.echo("\n⚠️  To activate nginx run:")
                click.echo(f"   sudo cp {config_path} /etc/nginx/sites-available/")
                click.echo(f"   sudo ln -s /etc/nginx/sites-available/tunnel-{name} /etc/nginx/sites-enabled/")
                click.echo("   sudo nginx -t")
                click.echo("   sudo systemctl reload nginx")
        
    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)


if __name__ == '__main__':
    nginx_cli()
