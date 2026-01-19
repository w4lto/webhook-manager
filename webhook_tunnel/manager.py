"""
Tunnel Manager - Core functionality for managing tunnels
"""
import os
import sys
import json
import socket
import subprocess
import signal
import time
import psutil
import shutil
import platform
import urllib.request
import hashlib
import tarfile
import zipfile
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Global configuration
CONFIG_DIR = Path.home() / '.webhook-tunnel'
CONFIG_FILE = CONFIG_DIR / 'config.json'
TUNNELS_FILE = CONFIG_DIR / 'tunnels.json'
LOG_DIR = CONFIG_DIR / 'logs'

class TunnelManager:
    """Tunnel manager."""
    
    def __init__(self):
        self.ensure_config_dir()
        self.config = self.load_config()
        self.tunnels = self.load_tunnels()
    
    def ensure_config_dir(self):
        """Ensure configuration directories exist."""
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
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        return self.load_json(CONFIG_FILE)
    
    def load_tunnels(self) -> Dict[str, Any]:
        """Load active tunnels."""
        if TUNNELS_FILE.exists():
            return self.load_json(TUNNELS_FILE)
        return {}
    
    def save_tunnels(self):
        """Persist active tunnels."""
        self.save_json(TUNNELS_FILE, self.tunnels)
    
    def save_config(self):
        """Persist configuration."""
        self.save_json(CONFIG_FILE, self.config)
    
    @staticmethod
    def load_json(filepath: Path) -> Dict:
        """Load a JSON file."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    @staticmethod
    def save_json(filepath: Path, data: Dict):
        """Write a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def is_port_available(self, port: int) -> bool:
        """Check whether a port is available."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0
    
    def is_port_in_use(self, port: int) -> bool:
        """Check whether a port is in use (inverse of is_port_available)."""
        return not self.is_port_available(port)
    
    def get_process_info(self, pid: int) -> Optional[Dict]:
        """Get process information."""
        try:
            process = psutil.Process(pid)
            return {
                'pid': pid,
                'name': process.name(),
                'status': process.status(),
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def create_tunnel(
        self,
        name: str,
        local_port: int,
        subdomain: Optional[str] = None,
        public_port: Optional[int] = None,
        public_provider: Optional[str] = None,
        interactive_public: bool = True,
    ) -> Dict:
        """Create a new tunnel."""
        if name in self.tunnels:
            raise ValueError(f"Túnel '{name}' já existe")
        
        # Ensure the local port is currently in use (your service must be running).
        if self.is_port_available(local_port):
            raise ValueError(
                f"Porta local {local_port} não está em uso. "
                f"Inicie seu serviço primeiro."
            )
        
        # Determine subdomain
        if not subdomain:
            subdomain = name
        
        # Determine public (gateway) port
        if not public_port:
            public_port = self.find_available_port()
        
        # Build hostname URL and a loopback URL (always resolvable)
        # Note: as a pip-installed tool, we cannot assume the user has custom DNS/hosts configured.
        # Therefore we always expose a 127.0.0.1 URL as well.

        domain = self.config.get('domain', 'localhost')
        public_host = f"{subdomain}.{domain}" if domain else subdomain
        public_url = f"http://{public_host}:{public_port}"
        local_url = f"http://127.0.0.1:{public_port}"
        curl_resolve = (
            f"curl --resolve {public_host}:{public_port}:127.0.0.1 "
            f"{public_url}"
        )
        
        tunnel_info = {
            'name': name,
            'local_port': local_port,
            'public_port': public_port,
            'subdomain': subdomain,
            'domain': domain,
            'public_url': public_url,
            'local_url': local_url,
            'public_host': public_host,
            'curl_resolve_example': curl_resolve,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'pid': None,
            # Public exposure (optional)
            'public_provider': None,
            'public_url_external': None,
            'public_pid': None,
            'requests_count': 0,
            'last_request': None,
        }
        
        # Start local proxy
        pid = self.start_proxy(tunnel_info)
        tunnel_info['pid'] = pid
        
        # Public exposure (optional)
        # As of this version, public exposure is always handled via localtunnel (npx/npm).
        if public_provider:
            provider = 'localtunnel'
            pub_pid, pub_url = self.start_public_localtunnel(tunnel_info, interactive=interactive_public)
            tunnel_info['public_provider'] = provider
            tunnel_info['public_pid'] = pub_pid
            tunnel_info['public_url_external'] = pub_url

        self.tunnels[name] = tunnel_info
        self.save_tunnels()
        
        return tunnel_info

    def start_public(self, name: str, provider: Optional[str] = None, interactive: bool = True) -> Dict:
        """Start (or restart) public exposure for an existing tunnel.

        - Does not recreate the local proxy.
        - Updates public_provider/public_pid/public_url_external.
        """
        if name not in self.tunnels:
            raise ValueError(f"Túnel '{name}' não encontrado")

        t = self.tunnels[name]
        proxy_pid = t.get('pid')
        if not proxy_pid or not self.get_process_info(proxy_pid):
            raise RuntimeError(
                f"Proxy local do túnel '{name}' não está em execução. Reinicie o túnel antes de expor publicamente."
            )

        # If already running, return as-is.
        if t.get('public_pid') and self.get_process_info(t.get('public_pid')):
            return t

        # Public exposure is always via localtunnel.
        prov = 'localtunnel'
        pub_pid, pub_url = self.start_public_localtunnel(t, interactive=interactive)

        t['public_provider'] = prov
        t['public_pid'] = pub_pid
        t['public_url_external'] = pub_url
        self.save_tunnels()
        return t

    def stop_public(self, name: str) -> Dict:
        """Stop only the public provider (keeps the local proxy running)."""
        if name not in self.tunnels:
            raise ValueError(f"Túnel '{name}' não encontrado")

        t = self.tunnels[name]
        pub_pid = t.get('public_pid')
        if pub_pid:
            try:
                p = psutil.Process(pub_pid)
                p.terminate()
                try:
                    p.wait(timeout=3)
                except psutil.TimeoutExpired:
                    p.kill()
            except psutil.NoSuchProcess:
                pass

        t['public_pid'] = None
        t['public_url_external'] = None
        # Keep public_provider to make re-enabling easier
        self.save_tunnels()
        return t

    def _prompt_yes_no(self, question: str, default_yes: bool = True) -> bool:
        """Simple, portable yes/no prompt (no external dependencies)."""
        if not sys.stdin.isatty():
            return False
        default = "Y/n" if default_yes else "y/N"
        while True:
            try:
                ans = input(f"{question} ({default}): ").strip().lower()
            except EOFError:
                return False
            if not ans:
                return default_yes
            if ans in ("y", "yes", "s", "sim"):
                return True
            if ans in ("n", "no", "nao", "não"):
                return False
            print("Please answer with 'y'/'n'.")

    def _tools_dir(self) -> Path:
        d = CONFIG_DIR / 'tools'
        d.mkdir(exist_ok=True)
        return d

    def _node_install_dir(self) -> Path:
        d = self._tools_dir() / 'node'
        d.mkdir(exist_ok=True)
        return d

    def _detect_node_platform(self) -> (str, str):
        """Return (os_id, arch_id) in the format used by Node.js distributions."""
        sys_plat = sys.platform
        machine = platform.machine().lower()
        if sys_plat.startswith('linux'):
            os_id = 'linux'
        elif sys_plat == 'darwin':
            os_id = 'darwin'
        elif sys_plat in ('win32', 'cygwin', 'msys'):
            os_id = 'win'
        else:
            raise RuntimeError(f"Plataforma não suportada para auto-instalação do Node.js: {sys_plat}")

        if machine in ('x86_64', 'amd64'):
            arch_id = 'x64'
        elif machine in ('aarch64', 'arm64'):
            arch_id = 'arm64'
        else:
            raise RuntimeError(f"Arquitetura não suportada para Node.js portátil: {machine}")

        return os_id, arch_id

    def _fetch_json(self, url: str) -> Any:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))

    def _download_file(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, 'wb') as f:
            shutil.copyfileobj(r, f)

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()

    def ensure_npx(self, interactive: bool = True) -> str:
        """Return the path to 'npx'. If missing, optionally download a portable Node.js."""
        npx = shutil.which('npx')
        if npx:
            return npx

        # Have we already installed a bundled Node.js?
        installed = self.config.get('bundled_node') or {}
        npx_path = installed.get('npx_path')
        if npx_path and Path(npx_path).exists():
            return npx_path

        if not interactive:
            raise RuntimeError("npx não encontrado.")

        ok = self._prompt_yes_no(
            "Node.js/npm (npx) não encontrados. Deseja baixar e instalar uma versão portátil automaticamente?",
            default_yes=True,
        )
        if not ok:
            raise RuntimeError(
                "npx não encontrado. Instale Node.js (que inclui npm/npx) ou execute sem '--public'."
            )

        npx = self.install_portable_node_lts()
        return npx

    def install_portable_node_lts(self) -> str:
        """Download and install a portable Node.js LTS into ~/.webhook-tunnel/tools/node."""
        os_id, arch_id = self._detect_node_platform()

        # Discover the most recent LTS version via Node.js index.json
        index_url = 'https://nodejs.org/dist/index.json'
        entries = self._fetch_json(index_url)
        lts_entries = [e for e in entries if e.get('lts')]
        if not lts_entries:
            raise RuntimeError("Não foi possível localizar uma versão LTS do Node.js em index.json")
        version = lts_entries[0]['version']  # index.json costuma vir em ordem decrescente

        # Archive and install directory
        base = f"node-{version}-{os_id}-{arch_id}"
        if os_id == 'win':
            filename = f"{base}.zip"
        else:
            filename = f"{base}.tar.xz"

        dist_base = f"https://nodejs.org/dist/{version}"
        archive_url = f"{dist_base}/{filename}"
        shasums_url = f"{dist_base}/SHASUMS256.txt"

        install_root = self._node_install_dir() / version
        install_root.mkdir(parents=True, exist_ok=True)
        archive_path = install_root / filename
        shasums_path = install_root / 'SHASUMS256.txt'

        # Download files
        self._download_file(shasums_url, shasums_path)
        self._download_file(archive_url, archive_path)

        # Verify SHA256
        expected = None
        for line in shasums_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            if line.strip().endswith(filename):
                expected = line.split()[0]
                break
        if expected:
            got = self._sha256(archive_path)
            if got != expected:
                raise RuntimeError(
                    f"Checksum inválido do Node.js ({filename}). Esperado {expected}, obtido {got}."
                )

        # Extract
        extract_dir = install_root / base
        if extract_dir.exists():
            # Already extracted
            pass
        else:
            if os_id == 'win':
                with zipfile.ZipFile(archive_path, 'r') as z:
                    z.extractall(install_root)
            else:
                with tarfile.open(archive_path, 'r:*') as t:
                    t.extractall(install_root)

        # Compute paths
        if os_id == 'win':
            npx_path = str(extract_dir / 'npx.cmd')
        else:
            npx_path = str(extract_dir / 'bin' / 'npx')

        if not Path(npx_path).exists():
            raise RuntimeError(
                f"Instalação do Node.js concluída, mas npx não foi encontrado em {npx_path}."
            )

        # Persist config
        self.config['bundled_node'] = {
            'version': version,
            'os': os_id,
            'arch': arch_id,
            'root': str(extract_dir),
            'npx_path': npx_path,
        }
        self.save_config()

        return npx_path

    def start_public_localtunnel(self, tunnel_info: Dict, interactive: bool = True) -> (int, str):
        """Expose the local gateway port via localtunnel (npx).

        interactive:
          - True  -> may prompt to install a portable Node.js (via stdin)
          - False -> never prompts; fails if npx is not available
        """
        name = tunnel_info['name']
        local_forward_port = int(tunnel_info['public_port'])
        log_file = LOG_DIR / f"{name}.public.localtunnel.log"

        npx = self.ensure_npx(interactive=interactive)
        cmd = [npx, 'localtunnel', '--port', str(local_forward_port)]

        url_re = re.compile(r"(https?://[^\s]+)")
        public_url: Optional[str] = None

        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )

        start_time = time.time()
        timeout_sec = 20.0
        try:
            while time.time() - start_time < timeout_sec:
                if process.poll() is not None:
                    raise RuntimeError(f"Falha ao iniciar localtunnel. Veja o log: {log_file}")

                line = ''
                if process.stdout:
                    line = process.stdout.readline()

                if not line:
                    time.sleep(0.05)
                    continue

                with open(log_file, 'a') as log:
                    log.write(line)
                    log.flush()

                m = url_re.search(line)
                if m:
                    # localtunnel prints multiple lines; the public URL is what matters.
                    public_url = m.group(1)
                    break
        except Exception:
            try:
                process.terminate()
            except Exception:
                pass
            raise

        if not public_url:
            raise RuntimeError(
                f"Timeout ao capturar URL pública do localtunnel. Veja o log: {log_file}"
            )

        return process.pid, public_url

    # Note: support for other providers (e.g., Pinggy) was removed in this version.
    # This tool uses localtunnel exclusively via npx/npm to keep the workflow plug-and-play.
    
    def find_available_port(self, start: int = 8000, end: int = 9000) -> int:
        """Find an available port."""
        for port in range(start, end):
            if self.is_port_available(port):
                # Ensure the port is not already reserved by another tunnel
                if not any(t.get('public_port') == port for t in self.tunnels.values()):
                    return port
        raise RuntimeError("Nenhuma porta disponível encontrada")
    
    def start_proxy(self, tunnel_info: Dict) -> int:
        """Start an embedded local proxy (no OS-specific binaries).

        Implementation: spawn a Python subprocess executing
        webhook_tunnel.proxy, which performs TCP forwarding and records basic events
        and HTTP requests (best-effort) into the tunnel log file.
        """
        local_port = tunnel_info['local_port']
        public_port = tunnel_info['public_port']
        name = tunnel_info['name']
        
        log_file = LOG_DIR / f"{name}.log"
        
        cmd = [
            sys.executable,
            "-m",
            "webhook_tunnel.proxy",
            "--name",
            str(name),
            "--public-port",
            str(public_port),
            "--local-port",
            str(local_port),
            "--log-file",
            str(log_file),
        ]
        
        # Start process in the background
        # We keep stdout/stderr redirected into the same log file.
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        
        # Wait briefly to ensure the process has started
        time.sleep(0.5)
        
        # Verify the process is still running
        if process.poll() is not None:
            raise RuntimeError(
                f"Falha ao iniciar proxy. Veja o log: {log_file}\n"
                f"Comando: {' '.join(cmd)}"
            )
        
        return process.pid
    
    def stop_tunnel(self, name: str):
        """Stop a tunnel."""
        if name not in self.tunnels:
            raise ValueError(f"Túnel '{name}' não encontrado")
        
        tunnel = self.tunnels[name]
        pid = tunnel.get('pid')

        # Stop public exposure (localtunnel via npx/npm)
        pub_pid = tunnel.get('public_pid')
        if pub_pid:
            try:
                p = psutil.Process(pub_pid)
                p.terminate()
                try:
                    p.wait(timeout=3)
                except psutil.TimeoutExpired:
                    p.kill()
            except psutil.NoSuchProcess:
                pass
        
        if pid:
            try:
                process = psutil.Process(pid)
                process.terminate()
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    process.kill()
            except psutil.NoSuchProcess:
                pass
        
        del self.tunnels[name]
        self.save_tunnels()
    
    def restart_tunnel(self, name: str):
        """Restart a tunnel."""
        if name not in self.tunnels:
            raise ValueError(f"Túnel '{name}' não encontrado")
        
        tunnel = self.tunnels[name]
        local_port = tunnel['local_port']
        subdomain = tunnel['subdomain']
        public_port = tunnel['public_port']
        public_provider = tunnel.get('public_provider')
        
        self.stop_tunnel(name)
        return self.create_tunnel(name, local_port, subdomain, public_port, public_provider)
    
    def list_tunnels(self) -> Dict[str, Dict]:
        """List all tunnels."""
        # Refresh tunnel status
        for name, tunnel in self.tunnels.items():
            pid = tunnel.get('pid')
            if pid:
                info = self.get_process_info(pid)
                if info:
                    tunnel['process_info'] = info
                    tunnel['status'] = 'running'
                else:
                    tunnel['status'] = 'dead'
        
        return self.tunnels
    
    def get_tunnel(self, name: str) -> Optional[Dict]:
        """Get information for a specific tunnel."""
        return self.tunnels.get(name)
    
    def cleanup_dead_tunnels(self) -> List[str]:
        """Remove tunnels whose processes have exited."""
        dead_tunnels = []
        
        for name, tunnel in list(self.tunnels.items()):
            pid = tunnel.get('pid')
            if pid:
                try:
                    psutil.Process(pid)
                except psutil.NoSuchProcess:
                    dead_tunnels.append(name)
                    del self.tunnels[name]
        
        if dead_tunnels:
            self.save_tunnels()
        
        return dead_tunnels
    
    def stop_all_tunnels(self):
        """Stop all tunnels."""
        tunnel_names = list(self.tunnels.keys())
        for name in tunnel_names:
            try:
                self.stop_tunnel(name)
            except Exception:
                pass
    
    def get_logs(self, name: str, lines: int = 50) -> str:
        """Read tunnel logs."""
        log_file = LOG_DIR / f"{name}.log"
        lt_file = LOG_DIR / f"{name}.public.localtunnel.log"
        
        if not log_file.exists():
            return ""
        
        try:
            parts: List[str] = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    all_lines = f.readlines()
                    parts.append(''.join(all_lines[-lines:]))

            # Public provider logs (if any)
            if lt_file.exists():
                with open(lt_file, 'r') as f:
                    all_lines = f.readlines()
                    parts.append("\n--- [public: localtunnel] ---\n")
                    parts.append(''.join(all_lines[-lines:]))

            return ''.join(parts)
        except Exception as e:
            return f"Error while reading logs: {e}"
    
    def get_stats(self) -> Dict:
        """Get overall statistics."""
        total_tunnels = len(self.tunnels)
        active_tunnels = sum(1 for t in self.tunnels.values() 
                           if self.get_process_info(t.get('pid')))
        
        total_cpu = 0
        total_memory = 0
        
        for tunnel in self.tunnels.values():
            pid = tunnel.get('pid')
            if pid:
                info = self.get_process_info(pid)
                if info:
                    total_cpu += info['cpu_percent']
                    total_memory += info['memory_mb']
        
        return {
            'total_tunnels': total_tunnels,
            'active_tunnels': active_tunnels,
            'dead_tunnels': total_tunnels - active_tunnels,
            'total_cpu_percent': round(total_cpu, 2),
            'total_memory_mb': round(total_memory, 2),
        }
