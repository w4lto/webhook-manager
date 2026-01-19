from datetime import datetime
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, DataTable, Static, Label, 
    Button, Input, Log, TabbedContent, TabPane, Checkbox
)
from textual.binding import Binding
from textual.timer import Timer
from rich.text import Text

from .manager import TunnelManager


class ConfirmInstallNode(Screen[bool]):
    """Confirm installation of the portable Node.js runtime (for localtunnel)."""

    BINDINGS = [
        Binding("y", "yes", "Yes", show=False),
        Binding("n", "no", "No", show=False),
        Binding("escape", "no", "No", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "[bold]Node.js/npm (npx) não encontrados.[/bold]\n\n"
                "Para usar o provider [cyan]localtunnel[/cyan], o TUI pode baixar e instalar uma versão portátil\n"
                "em [dim]~/.webhook-tunnel/tools/node[/dim] (sem package manager do sistema).\n\n"
                "Deseja instalar agora?",
                id="confirm-text",
            ),
            Horizontal(
                Button("Install", variant="success", id="yes"),
                Button("Cancel", variant="error", id="no"),
                classes="button-group",
            ),
            id="confirm-box",
        )

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self) -> None:
        self.dismiss(False)


class TunnelStats(Static):
    """Widget to display statistics."""
    
    def __init__(self):
        super().__init__()
        self.manager: Optional[TunnelManager] = None
    
    def on_mount(self) -> None:
        """Refresh statistics periodically."""
        # Share the same App manager to avoid state divergence.
        self.manager = getattr(self.app, "manager", None) or TunnelManager()
        self.set_interval(2.0, self.update_stats)
        self.update_stats()
    
    def update_stats(self) -> None:
        """Refresh statistics."""
        if not self.manager:
            return
        stats = self.manager.get_stats()
        
        content = f"""[bold cyan]📊 Tunnel Statistics[/bold cyan]
        
[green]Active:[/green] {stats['active_tunnels']}/{stats['total_tunnels']} tunnels
[yellow]CPU:[/yellow] {stats['total_cpu_percent']}%
[blue]Memory:[/blue] {stats['total_memory_mb']:.1f} MB
[red]Dead:[/red] {stats['dead_tunnels']} tunnels
"""
        self.update(content)


class TunnelTable(DataTable):
    """Tunnel table."""
    
    BINDINGS = [
        Binding("enter", "select_tunnel", "Details", show=True),
        Binding("d", "delete_tunnel", "Delete", show=True),
        Binding("r", "restart_tunnel", "Restart", show=True),
        Binding("l", "view_logs", "Logs", show=True),
        Binding("p", "toggle_public", "Public", show=True),
    ]
    
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.manager: Optional[TunnelManager] = None
    
    def on_mount(self) -> None:
        """Configure the table."""
        # Share the same App manager to avoid state divergence.
        self.manager = getattr(self.app, "manager", None) or TunnelManager()
        self.add_columns(
            "NAME",
            "STATUS",
            "PUB",
            "LOCAL",
            "GW",
            "HOST",
            "EXT",
            "CPU%",
            "MEM(MB)",
            "UPTIME",
        )
        self.set_interval(1.0, self.refresh_tunnels)
        self.refresh_tunnels()

    @staticmethod
    def _truncate(value: str, max_len: int = 34) -> str:
        """Truncate long strings to keep the table readable."""
        if not value:
            return ""
        value = str(value)
        if len(value) <= max_len:
            return value
        return value[: max_len - 1] + "…"
    
    def refresh_tunnels(self) -> None:
        """Refresh the tunnel list."""
        if not self.manager:
            return
        self.clear()
        tunnels = self.manager.list_tunnels()
        
        for name, tunnel in tunnels.items():
            status_color = "green" if tunnel.get('status') == 'running' else "red"
            status = Text(f"● {tunnel.get('status','?')}", style=status_color)
            
            process_info = tunnel.get('process_info', {})
            cpu = f"{process_info.get('cpu_percent', 0):.1f}"
            memory = f"{process_info.get('memory_mb', 0):.1f}"
            
            # Compute uptime.
            created = datetime.fromisoformat(tunnel['created_at'])
            uptime = datetime.now() - created
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds.
            
            public_host = tunnel.get("public_host") or ""
            local_url = tunnel.get("local_url") or tunnel.get("public_url") or ""
            ext_url = tunnel.get("public_url_external") or ""

            provider = tunnel.get("public_provider")
            pub_pid = tunnel.get("public_pid")
            pub_running = bool(pub_pid and self.manager.get_process_info(pub_pid))

            # PUB column: provider status (separate from the local proxy).
            pub_cell = "-"
            if provider:
                dot = "●" if pub_running else "○"
                pub_cell = f"{dot} {provider}"

            # GW column: show only the local gateway port (local proxy).
            gw_cell = f":{tunnel['public_port']}"

            self.add_row(
                name,
                status,
                self._truncate(pub_cell, 18) if pub_cell else "-",
                f":{tunnel['local_port']}",
                gw_cell,
                self._truncate(public_host, 26),
                self._truncate(ext_url, 42) if ext_url else "",
                cpu,
                memory,
                uptime_str,
                key=name,
            )
    
    def action_delete_tunnel(self) -> None:
        """Delete the selected tunnel."""
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
        tunnel_name = row_key.value
        
        if tunnel_name:
            try:
                self.manager.stop_tunnel(tunnel_name)
                self.app.notify(f"Tunnel '{tunnel_name}' stopped", severity="information")
                self.refresh_tunnels()
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error")
    
    def action_restart_tunnel(self) -> None:
        """Restart the selected tunnel."""
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
        tunnel_name = row_key.value
        
        if tunnel_name:
            try:
                self.manager.restart_tunnel(tunnel_name)
                self.app.notify(f"Tunnel '{tunnel_name}' restarted", severity="information")
                self.refresh_tunnels()
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error")

    def action_select_tunnel(self) -> None:
        """Show quick details for the selected tunnel."""
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
        tunnel_name = row_key.value
        if not tunnel_name:
            return

        t = self.manager.get_tunnel(tunnel_name) or {}
        local_url = t.get("local_url") or ""
        host_url = t.get("public_url") or ""
        ext_url = t.get("public_url_external") or ""
        provider = t.get("public_provider") or "-"

        msg = f"{tunnel_name} | Local: {local_url} | Host: {host_url} | Public({provider}): {ext_url or 'n/a'}"
        self.app.notify(msg, severity="information")
    
    def action_view_logs(self) -> None:
        """View tunnel logs."""
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
        tunnel_name = row_key.value
        
        if tunnel_name:
            # Habilita e muda para a aba de logs
            logs_pane = self.app.query_one("#logs-pane", TabPane)
            logs_pane.disabled = False

            tabbed_content = self.app.query_one(TabbedContent)
            tabbed_content.active = "logs-pane"

            # Delegar ao App (permite auto-refresh)
            if hasattr(self.app, "set_current_log_tunnel"):
                self.app.set_current_log_tunnel(tunnel_name)
            else:
                logs_widget = self.app.query_one("#logs-content", Log)
                logs_content = self.manager.get_logs(tunnel_name)
                logs_widget.clear()
                logs_widget.write(logs_content if logs_content else "No logs available")

    def action_toggle_public(self) -> None:
        """Toggle public exposure (provider) without recreating the tunnel."""
        if not self.manager:
            return
        row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
        tunnel_name = row_key.value
        if not tunnel_name:
            return

        t = self.manager.get_tunnel(tunnel_name) or {}
        pub_pid = t.get("public_pid")
        pub_running = bool(pub_pid and self.manager.get_process_info(pub_pid))

        # Delegate to the App so we can prompt/install Node from within the TUI.
        if hasattr(self.app, "toggle_public_for_tunnel"):
            self.app.toggle_public_for_tunnel(tunnel_name, currently_running=pub_running)
        else:
            try:
                if pub_running:
                    self.manager.stop_public(tunnel_name)
                    self.app.notify(f"Public provider stopped for '{tunnel_name}'", severity="information")
                else:
                    self.manager.start_public(tunnel_name, provider='localtunnel', interactive=False)
                    self.app.notify(f"Public provider started for '{tunnel_name}'", severity="information")
                self.refresh_tunnels()
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error")


class CreateTunnelForm(Container):
    """Form for creating a new tunnel."""
    
    def compose(self) -> ComposeResult:
        yield Label("Create New Tunnel", classes="form-title")
        yield Label("Name:")
        yield Input(placeholder="myapi", id="tunnel-name")
        yield Label("Local Port:")
        yield Input(placeholder="3000", id="local-port")
        yield Label("Subdomain (optional):")
        yield Input(placeholder="api", id="subdomain")
        yield Label("Public Port (optional):")
        yield Input(placeholder="8000", id="public-port")
        yield Checkbox("Expose publicly via npm (localtunnel)", id="public-enabled")
        yield Horizontal(
            Button("Create", variant="success", id="create-btn"),
            Button("Cancel", variant="error", id="cancel-btn"),
            classes="button-group"
        )


class TunnelApp(App):
    """Main TUI application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    Header {
        background: $accent;
    }
    
    Footer {
        background: $panel;
    }
    
    TunnelStats {
        height: 8;
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    
    DataTable {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    DataTable > .datatable--cursor {
        background: $accent 50%;
    }
    
    CreateTunnelForm {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }

    
    .form-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .button-group {
        margin-top: 1;
        width: 100%;
        height: auto;
    }
    
    .button-group Button {
        width: 1fr;
        margin: 0 1;
    }
    
    Log {
        border: solid $primary;
        height: 1fr;
    }

    #logs-meta {
        height: auto;
        border: solid $primary;
        padding: 1;
        margin: 1;
        background: $panel;
    }
    
    #notification-area {
        dock: top;
        height: auto;
        background: $panel;
        padding: 1;
    }

    #confirm-box {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
        align: center middle;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "create_tunnel", "Create", show=True),
        Binding("x", "cleanup", "Cleanup", show=True),
        Binding("k", "stop_all", "Stop All", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("tab", "next_tab", "Next Tab", show=False),
    ]
    
    TITLE = "Webhook Tunnel Mannager"
    SUB_TITLE = "Press ? for help"
    
    def __init__(self):
        super().__init__()
        self.manager = TunnelManager()
        self._current_log_tunnel: Optional[str] = None
        self._last_logs_snapshot: str = ""
        self._logs_timer: Optional[Timer] = None

    def _ensure_npx_for_localtunnel(self, callback) -> None:
        """Ensure npx is available.

        If missing, open a TUI modal asking whether to install a portable Node.js runtime.
        callback(ok: bool) will be invoked afterwards.
        """
        try:
            self.manager.ensure_npx(interactive=False)
            callback(True)
            return
        except Exception:
            pass

        def _after(answer: bool) -> None:
            if not answer:
                callback(False)
                return
            try:
                self.notify("Installing portable Node.js (LTS)...", severity="information")
                self.manager.install_portable_node_lts()
                callback(True)
            except Exception as e:
                self.notify(f"Node install failed: {e}", severity="error")
                callback(False)

        self.push_screen(ConfirmInstallNode(), _after)

    def toggle_public_for_tunnel(self, name: str, currently_running: bool = False) -> None:
        """Safely toggle public exposure via localtunnel (npm) within the TUI."""
        if currently_running:
            try:
                self.manager.stop_public(name)
                self.notify(f"Public provider stopped for '{name}'", severity="information")
            except Exception as e:
                self.notify(f"Error: {e}", severity="error")
            table = self.query_one(TunnelTable)
            table.refresh_tunnels()
            return

        # Public exposure is always via localtunnel in this version.
        self._ensure_npx_for_localtunnel(lambda ok: self._start_public_after_node(ok, name))

    def _start_public_after_node(self, ok: bool, name: str) -> None:
        if not ok:
            return
        try:
            self.manager.start_public(name, provider='localtunnel', interactive=False)
            self.notify(f"Public provider started for '{name}'", severity="information")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        table = self.query_one(TunnelTable)
        table.refresh_tunnels()

    def set_current_log_tunnel(self, name: str) -> None:
        """Set the current tunnel for log viewing and start auto-refresh."""
        self._current_log_tunnel = name
        self._refresh_logs(force=True)
        if self._logs_timer is None:
            self._logs_timer = self.set_interval(1.0, self._refresh_logs)

    def _refresh_logs(self, force: bool = False) -> None:
        """Refresh the logs panel (best-effort)."""
        if not self._current_log_tunnel:
            return

        # Refresh tunnel metadata (URLs/provider) at the top of the Logs panel.
        try:
            t = self.manager.get_tunnel(self._current_log_tunnel) or {}
            public_url = t.get("public_url") or ""
            local_url = t.get("local_url") or ""
            ext_url = t.get("public_url_external") or ""
            provider = t.get("public_provider") or "-"
            curl_resolve = t.get("curl_resolve_example") or ""
            meta_lines = [
                f"[bold]Tunnel:[/bold] {self._current_log_tunnel}",
                f"[bold]Local URL:[/bold] {local_url}",
                f"[bold]Host URL:[/bold] {public_url}",
                f"[bold]Public Provider:[/bold] {provider}",
            ]
            if ext_url:
                meta_lines.append(f"[bold]External URL:[/bold] {ext_url}")
            if curl_resolve:
                meta_lines.append(f"[dim]curl:[/dim] {curl_resolve}")

            meta = "\n".join(meta_lines)
            meta_widget = self.query_one("#logs-meta", Static)
            meta_widget.update(meta)
        except Exception:
            pass

        try:
            logs_content = self.manager.get_logs(self._current_log_tunnel, lines=300)
        except Exception as e:
            logs_content = f"Error reading logs: {e}"

        if not logs_content:
            logs_content = "No logs available"

        if (not force) and (logs_content == self._last_logs_snapshot):
            return

        self._last_logs_snapshot = logs_content
        try:
            logs_widget = self.query_one("#logs-content", Log)
            logs_widget.clear()
            logs_widget.write(logs_content)
        except Exception:
            # The UI might not be mounted yet; ignore.
            pass
    
    def compose(self) -> ComposeResult:
        """Cria a interface"""
        yield Header()
        
        with TabbedContent():
            with TabPane("Tunnels", id="tunnels-pane"):
                yield TunnelStats()
                yield TunnelTable()
            
            with TabPane("Create", id="create-pane"):
                yield CreateTunnelForm()
            
            with TabPane("Logs", id="logs-pane", disabled=True):
                yield Static("Select a tunnel and press 'l' to view logs.", id="logs-meta")
                yield Log(id="logs-content", highlight=True)
            
            with TabPane("Help", id="help-pane"):
                yield Static("""
[bold cyan]🚇 Webhook Tunnel - Keyboard Shortcuts[/bold cyan]

[bold yellow]Navigation:[/bold yellow]
  ↑/↓         - Navigate tunnels
  Enter       - View tunnel details
  Tab         - Switch tabs
  
[bold yellow]Tunnel Management:[/bold yellow]
  c           - Create new tunnel
  d           - Delete selected tunnel
  r           - Restart selected tunnel
  p           - Toggle public provider (start/stop)
  l           - View logs
  x           - Cleanup dead tunnels
  k           - Stop all tunnels
  
[bold yellow]General:[/bold yellow]
  ?           - Show this help
  q           - Quit application

[bold green]Tips:[/bold green]
  • Tunnels refresh automatically every second
  • CPU and memory usage are updated in real-time
  • Logs are displayed in the Logs tab
  • Use Public Provider (e.g. 'localtunnel') to get an External URL for webhook testing
  • Use arrow keys to navigate the table
                """, id="help-content")
        
        yield Footer()
    
    def action_create_tunnel(self) -> None:
        """Switch to the Create tab."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "create-pane"
        
        
    
    def action_cleanup(self) -> None:
        """Clean up dead tunnels."""
        dead = self.manager.cleanup_dead_tunnels()
        if dead:
            self.notify(f"Cleaned up {len(dead)} dead tunnel(s)", severity="information")
        else:
            self.notify("No dead tunnels found", severity="information")
        
        # Refresh table
        table = self.query_one(TunnelTable)
        table.refresh_tunnels()
    
    def action_stop_all(self) -> None:
        """Stop all tunnels."""
        count = len(self.manager.tunnels)
        if count > 0:
            self.manager.stop_all_tunnels()
            self.notify(f"Stopped {count} tunnel(s)", severity="warning")
            
            # Refresh table
            table = self.query_one(TunnelTable)
            table.refresh_tunnels()
        else:
            self.notify("No active tunnels", severity="information")
    
    def action_help(self) -> None:
        """Mostra ajuda"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "help-pane"
    
    def action_next_tab(self) -> None:
        """Next tab."""
        tabbed_content = self.query_one(TabbedContent)
        tabs = ["tunnels-pane", "create-pane", "logs-pane", "help-pane"]
        current = tabbed_content.active
        
        # Find the next enabled tab
        current_idx = tabs.index(current) if current in tabs else 0
        next_idx = (current_idx + 1) % len(tabs)
        
        while next_idx != current_idx:
            tab_id = tabs[next_idx]
            tab = self.query_one(f"#{tab_id}", TabPane)
            if not tab.disabled:
                tabbed_content.active = tab_id
                break
            next_idx = (next_idx + 1) % len(tabs)
    
    @on(Button.Pressed, "#create-btn")
    def handle_create_tunnel(self) -> None:
        """Create a new tunnel."""
        name_input = self.query_one("#tunnel-name", Input)
        port_input = self.query_one("#local-port", Input)
        subdomain_input = self.query_one("#subdomain", Input)
        public_port_input = self.query_one("#public-port", Input)
        public_enabled_cb = self.query_one("#public-enabled", Checkbox)
        
        name = name_input.value.strip()
        port_str = port_input.value.strip()
        subdomain = subdomain_input.value.strip() or None
        public_port_str = public_port_input.value.strip()
        public_enabled = bool(public_enabled_cb.value)
        public_provider = 'localtunnel' if public_enabled else None
        
        if not name or not port_str:
            self.notify("Name and port are required", severity="error")
            return
        
        try:
            local_port = int(port_str)
            public_port = int(public_port_str) if public_port_str else None

            def _finish_create(ok: bool) -> None:
                if not ok:
                    return

                self.manager.create_tunnel(
                    name,
                    local_port,
                    subdomain,
                    public_port,
                    public_provider,
                    interactive_public=False,
                )
                self.notify(f"Tunnel '{name}' created successfully!", severity="information")

                # Clear form
                name_input.value = ""
                port_input.value = ""
                subdomain_input.value = ""
                public_port_input.value = ""
                public_enabled_cb.value = False

                # Return to the Tunnels tab
                tabbed_content = self.query_one(TabbedContent)
                tabbed_content.active = "tunnels-pane"

                # Refresh table
                table = self.query_one(TunnelTable)
                table.refresh_tunnels()

            # If the user enabled public exposure, ensure npx is available without breaking the UI.
            if public_enabled:
                self._ensure_npx_for_localtunnel(_finish_create)
            else:
                _finish_create(True)
            
        except ValueError as e:
            self.notify(f"Error: {e}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected error: {e}", severity="error")
    
    def clear_form(self) -> None:
        self.query_one("#tunnel-name", Input).value = ""
        self.query_one("#local-port", Input).value = ""
        self.query_one("#subdomain", Input).value = ""
        self.query_one("#public-port", Input).value = ""
        self.query_one("#public-enabled", Checkbox).value = False
    
    @on(Button.Pressed, "#cancel-btn")
    def handle_cancel(self) -> None:
        
        """Cancel creation."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "tunnels-pane"
        self.clear_form()


def main():
    """Entry point para TUI"""
    app = TunnelApp()
    app.run()


if __name__ == "__main__":
    main()
