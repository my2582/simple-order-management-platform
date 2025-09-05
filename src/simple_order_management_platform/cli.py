"""Command-Line Interface for Simple Order Management Platform."""

import logging
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table

from .config.loader import config_loader
from .core.connector import IBConnector
from .core.orchestrator import DataOrchestrator
from .providers.ib import IBProvider
from .models.base import InstrumentType
from .utils.exporters import export_multi_asset_results
from .utils.exceptions import SimpleOrderManagementPlatformError, ConnectionError

app = typer.Typer(
    name="simple-order",
    help="Simple Order Management Platform with multi-asset market data capabilities",
    rich_markup_mode="rich"
)
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.command()
def download(
    strategy: str = typer.Argument(..., help="Strategy name to execute"),
    instrument_types: Optional[List[str]] = typer.Option(
        None, "--types", "-t",
        help="Instrument types to download (futures,stocks,etfs). Default: all types in strategy"
    ),
    version: Optional[str] = typer.Option(
        None, "--version", "-v",
        help="Strategy version. Default: latest version"
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output Excel filename. Default: auto-generated"
    ),
    test_mode: bool = typer.Option(
        False, "--test",
        help="Test mode with limited data"
    ),
    # IB connection overrides
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Download market data for specified strategy and instrument types."""
    
    console.print(f"[bold blue]🚀 Starting data download for strategy '{strategy}'[/bold blue]")

    try:
        # Load app configuration
        app_config = config_loader.load_app_config()
        
        # Parse instrument types
        parsed_instrument_types: Optional[List[InstrumentType]] = None
        if instrument_types:
            parsed_instrument_types = []
            for type_str in instrument_types:
                try:
                    parsed_instrument_types.append(InstrumentType(type_str.strip().lower()))
                except ValueError:
                    valid_types = [e.value for e in InstrumentType]
                    console.print(f"[red]❌ Invalid instrument type: '{type_str}'. "
                                f"Valid types: {', '.join(valid_types)}[/red]")
                    raise typer.Exit(1)
        
        # Get IB connection settings with overrides
        ib_settings = app_config.ib_settings
        host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
        port = ib_port if ib_port is not None else ib_settings.get("port", 4001)
        client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

        # Execute download with IB connection
        with IBConnector(host=host, port=port, client_id=client_id) as connector:
            provider = IBProvider(connector)
            orchestrator = DataOrchestrator(provider)

            with console.status("[bold green]Processing data download..."):
                results_by_type = orchestrator.download_strategy_data(
                    strategy_name=strategy,
                    version=version,
                    instrument_types=parsed_instrument_types,
                    test_mode=test_mode
                )
            
            if not results_by_type:
                console.print("[yellow]⚠️ No data downloaded for specified strategy and types[/yellow]")
                raise typer.Exit(0)

            # Export results to Excel
            output_path = export_multi_asset_results(
                results_by_type=results_by_type,
                strategy_name=strategy,
                output_filename=output_filename
            )
            
            # Show summary
            total_successful = sum(
                sum(1 for success, _, _ in results.values() if success)
                for results in results_by_type.values()
            )
            total_failed = sum(len(results) for results in results_by_type.values()) - total_successful
            
            console.print(f"[green]✅ Download completed:[/green]")
            console.print(f"  • Successful: {total_successful}")
            console.print(f"  • Failed: {total_failed}")
            console.print(f"  • Output: [cyan]{output_path}[/cyan]")

    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during download")
        raise typer.Exit(1)


@app.command()
def test_connection(
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port"), 
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID"),
):
    """Test connection to Interactive Brokers TWS/Gateway."""
    
    console.print("[bold blue]🔧 Testing Interactive Brokers connection[/bold blue]")
    
    try:
        app_config = config_loader.load_app_config()
        ib_settings = app_config.ib_settings
        
        host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
        port = ib_port if ib_port is not None else ib_settings.get("port", 4001)
        client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

        with IBConnector(host=host, port=port, client_id=client_id) as connector:
            if connector.is_connected():
                console.print(f"[green]✅ Connection successful to {host}:{port} (Client ID: {client_id})[/green]")
            else:
                console.print(f"[red]❌ Connection failed to {host}:{port}[/red]")
                raise typer.Exit(1)
                
    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Error during connection test")
        raise typer.Exit(1)


@app.command()
def list_strategies():
    """List all available strategies."""
    
    console.print("[bold blue]📋 Available Strategies[/bold blue]")
    
    try:
        strategies_config = config_loader.load_strategies_config()
        
        table = Table(title="Available Strategies")
        table.add_column("Strategy Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Versions", style="magenta")
        
        for strategy_name in strategies_config.list_strategies():
            strategy = strategies_config.get_strategy(strategy_name)
            table.add_row(
                strategy_name,
                strategy.description[:60] + "..." if len(strategy.description) > 60 else strategy.description,
                ", ".join(strategy.versions.keys())
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error listing strategies: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

@app.command()
def update_master(
    asset_types: List[str] = typer.Option(
        ["futures"], "--types", "-t",
        help="Asset types to update (futures,stocks,etfs)"
    ),
    force_update: bool = typer.Option(
        False, "--force",
        help="Force update even if data is recent"
    ),
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Update master universe data from IBKR."""
    
    console.print("[bold blue]🔄 Updating Master Universe Data[/bold blue]")
    
    try:
        from .core.master_manager import MasterUniverseManager
        
        # IB 연결 설정
        app_config = config_loader.load_app_config()
        ib_settings = app_config.ib_settings
        
        host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
        port = ib_port if ib_port is not None else ib_settings.get("port", 4001)
        client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

        # Master Manager 초기화
        master_manager = MasterUniverseManager()
        
        with IBConnector(host=host, port=port, client_id=client_id) as connector:
            provider = IBProvider(connector)
            
            with console.status("[bold green]Updating master data..."):
                results = master_manager.update_master_data(
                    provider=provider,
                    asset_types=asset_types,
                    force_update=force_update
                )
            
            # 결과 출력
            for asset_type, result in results.items():
                if result['success']:
                    console.print(f"✅ {asset_type.title()}: {result['updated']} symbols updated")
                else:
                    console.print(f"❌ {asset_type.title()}: {result['error']}")
            
    except Exception as e:
        console.print(f"[red]❌ Master update failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def build_strategy(
    strategy_name: str = typer.Argument(..., help="Strategy name to build"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Strategy version"),
    export_excel: bool = typer.Option(True, "--excel/--no-excel", help="Export to Excel"),
):
    """Build strategy-specific data view from master data."""
    
    console.print(f"[bold blue]🏗️ Building strategy data view: {strategy_name}[/bold blue]")
    
    try:
        from .core.strategy_builder import StrategyBuilder
        
        builder = StrategyBuilder()
        
        with console.status("[bold green]Building strategy view..."):
            result = builder.build_strategy_view(
                strategy_name=strategy_name,
                version=version,
                export_excel=export_excel
            )
        
        console.print(f"✅ Strategy view built successfully:")
        console.print(f"  • Parquet: {result['parquet_path']}")
        if export_excel and result.get('excel_path'):
            console.print(f"  • Excel: {result['excel_path']}")
        console.print(f"  • Symbols: {result['symbol_count']}")
        console.print(f"  • Date range: {result['date_range']}")
        
    except Exception as e:
        console.print(f"[red]❌ Strategy build failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_master():
    """List master universe status."""
    
    console.print("[bold blue]📊 Master Universe Status[/bold blue]")
    
    try:
        from .core.master_manager import MasterUniverseManager
        
        manager = MasterUniverseManager()
        status = manager.get_status()
        
        table = Table(title="Master Universe Status")
        table.add_column("Asset Type", style="cyan")
        table.add_column("Symbols", justify="right", style="magenta")
        table.add_column("Last Updated", style="yellow")
        table.add_column("Status", style="green")
        
        for asset_type, info in status.items():
            table.add_row(
                asset_type.title(),
                str(info['symbol_count']),
                info['last_updated'] or 'Never',
                info['status']
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Status check failed: {e}[/red]")
        raise typer.Exit(1)
