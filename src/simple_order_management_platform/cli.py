"""Command-Line Interface for Simple Order Management Platform."""

import logging
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import typer
from rich.console import Console
from rich.table import Table

from .config.loader import config_loader
from .core.connector import IBConnector

def get_ib_connection_params(app_config, ib_host=None, ib_port=None, ib_client_id=None):
    """Get IB connection parameters with alternative ports support."""
    ib_settings = app_config.ib_settings
    host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
    port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
    client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)
    alternative_ports = ib_settings.get("alternative_ports", [4002, 7496, 7497])
    
    return host, port, client_id, alternative_ports
from .core.orchestrator import DataOrchestrator
from .providers.ib import IBProvider
from .models.base import InstrumentType
from .utils.exporters import export_multi_asset_results, export_portfolio_snapshots
from .utils.ibkr_exporters import export_ibkr_portfolio_report
from .utils.exceptions import SimpleOrderManagementPlatformError, ConnectionError
from .services.portfolio_service import PortfolioService
# from .services.order_service import OrderService  # Legacy, not used in model portfolio system
from .services.automation_service import automated_portfolio_service
from .services.market_data_service import market_data_service
# Model portfolio imports are done within functions to avoid circular imports

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
        port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
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
        port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
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
        port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
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


@app.command()
def download_positions(
    accounts: Optional[List[str]] = typer.Option(
        None, "--accounts", "-a",
        help="Specific account IDs to download (comma-separated). If not provided, downloads all accounts."
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output Excel filename. Default: auto-generated with timestamp"
    ),
    # IB connection overrides
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Download portfolio positions for all or specified accounts."""
    
    console.print("[bold blue]📊 Starting portfolio positions download[/bold blue]")

    try:
        # Load app configuration
        app_config = config_loader.load_app_config()
        
        # Get IB connection settings with overrides
        ib_settings = app_config.ib_settings
        host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
        port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
        client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

        # Execute download with IB connection
        with IBConnector(host=host, port=port, client_id=client_id) as connector:
            provider = IBProvider(connector)
            portfolio_service = PortfolioService(provider)

            with console.status("[bold green]Downloading portfolio positions..."):
                # Parse account list if provided
                account_list = None
                if accounts:
                    if len(accounts) == 1 and ',' in accounts[0]:
                        # Handle comma-separated string
                        account_list = [acc.strip() for acc in accounts[0].split(',')]
                    else:
                        account_list = accounts
                
                multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_list)
            
            if not multi_portfolio.snapshots:
                console.print("[yellow]⚠️ No portfolio data downloaded[/yellow]")
                raise typer.Exit(0)

            # Export results to Excel
            output_path = export_portfolio_snapshots(
                multi_portfolio=multi_portfolio,
                output_filename=output_filename,
                include_summary=True
            )
            
            # Show summary
            combined_summary = multi_portfolio.get_combined_summary()
            
            console.print(f"[green]✅ Portfolio download completed:[/green]")
            console.print(f"  • Accounts processed: {combined_summary['total_accounts']}")
            console.print(f"  • Total positions: {combined_summary['total_positions']}")
            console.print(f"  • Total portfolio value: ${combined_summary['total_portfolio_value']:,.2f}")
            console.print(f"  • Output: [cyan]{output_path}[/cyan]")
            
            # Show per-account summary
            console.print(f"\n[bold blue]📋 Per-Account Summary:[/bold blue]")
            for snapshot in multi_portfolio.snapshots:
                account_summary = snapshot.get_positions_summary()
                console.print(f"  • Account {snapshot.account_id}: "
                             f"{len(account_summary['positions'])} positions, "
                             f"${account_summary['total_value']:,.2f} total value, "
                             f"{account_summary['cash_percentage']:.1f}% cash")

    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during positions download")
        raise typer.Exit(1)


@app.command()
def download_positions_ibkr(
    accounts: Optional[List[str]] = typer.Option(
        None, "--accounts", "-a",
        help="Specific account IDs to download (comma-separated). If not provided, downloads all accounts."
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output Excel filename. Default: auto-generated with timestamp"
    ),
    use_cached_prices: bool = typer.Option(
        False, "--cached-prices",
        help="Use cached market prices instead of live data (faster, may be less accurate)"
    ),
    # IB connection overrides
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Download portfolio positions in IBKR standard format with asset class mapping."""
    
    console.print("[bold blue]📊 Starting IBKR standard portfolio positions download[/bold blue]")

    try:
        # Load app configuration
        app_config = config_loader.load_app_config()
        
        # Get IB connection parameters with alternative ports
        host, port, client_id, alternative_ports = get_ib_connection_params(app_config, ib_host, ib_port, ib_client_id)

        # Execute download with IB connection
        with IBConnector(host=host, port=port, client_id=client_id, alternative_ports=alternative_ports) as connector:
            provider = IBProvider(connector)
            
            # Configure portfolio service 
            if use_cached_prices:
                console.print("[cyan]📊 Using cached prices for market data[/cyan]")
            else:
                console.print("[green]📈 Using live market data from IBKR (original working method)[/green]")
            
            portfolio_service = PortfolioService(provider, use_cached_prices=use_cached_prices)

            with console.status("[bold green]Downloading portfolio positions..."):
                # Parse account list if provided
                account_list = None
                if accounts:
                    if len(accounts) == 1 and ',' in accounts[0]:
                        # Handle comma-separated string
                        account_list = [acc.strip() for acc in accounts[0].split(',')]
                    else:
                        account_list = accounts
                
                multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_list)
            
            if not multi_portfolio.snapshots:
                console.print("[yellow]⚠️ No portfolio data downloaded[/yellow]")
                raise typer.Exit(0)

            # Export results to IBKR standard Excel format
            output_path = export_ibkr_portfolio_report(
                multi_portfolio=multi_portfolio,
                output_filename=output_filename,
                include_metadata=True,
                portfolio_service=portfolio_service  # Pass portfolio service for Account Alias access
            )
            
            # Show summary
            combined_summary = multi_portfolio.get_combined_summary()
            
            console.print(f"[green]✅ IBKR portfolio download completed:[/green]")
            console.print(f"  • Accounts processed: {combined_summary['total_accounts']}")
            console.print(f"  • Total positions: {combined_summary['total_positions']}")
            console.print(f"  • Total portfolio value: ${combined_summary['total_portfolio_value']:,.2f}")
            console.print(f"  • Output: [cyan]{output_path}[/cyan]")
            
            # Show per-account summary with asset class info
            console.print(f"\n[bold blue]📋 Per-Account Summary:[/bold blue]")
            for snapshot in multi_portfolio.snapshots:
                account_summary = snapshot.get_positions_summary()
                
                # Count asset classes
                asset_classes = set()
                from .models.universe import get_asset_class
                for pos in account_summary['positions']:
                    asset_class = get_asset_class(pos['Symbol'])
                    if asset_class:
                        asset_classes.add(asset_class)
                
                console.print(f"  • Account {snapshot.account_id}: "
                             f"{len(account_summary['positions'])} positions, "
                             f"${account_summary['total_value']:,.2f} total value, "
                             f"{account_summary['cash_percentage']:.1f}% cash, "
                             f"{len(asset_classes)} asset classes")

    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during IBKR positions download")
        raise typer.Exit(1)


@app.command()
def holdings(
    accounts: Optional[List[str]] = typer.Option(
        None, "--accounts", "-a",
        help="Specific account IDs to download (comma-separated). If not provided, downloads all accounts."
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output Excel filename. Default: auto-generated with timestamp"
    ),
    # IB connection overrides
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Download holdings table in IBKR standard format."""
    
    console.print("[bold blue]📊 Starting IBKR holdings table download[/bold blue]")

    try:
        # Load app configuration
        app_config = config_loader.load_app_config()
        
        # Get IB connection parameters with alternative ports
        host, port, client_id, alternative_ports = get_ib_connection_params(app_config, ib_host, ib_port, ib_client_id)

        # Execute download with IB connection
        with IBConnector(host=host, port=port, client_id=client_id, alternative_ports=alternative_ports) as connector:
            provider = IBProvider(connector)
            
            console.print("[green]📈 Using live market data from IBKR[/green]")
            portfolio_service = PortfolioService(provider, use_cached_prices=False)

            with console.status("[bold green]Downloading holdings data..."):
                # Parse account list if provided
                account_list = None
                if accounts:
                    if len(accounts) == 1 and ',' in accounts[0]:
                        # Handle comma-separated string
                        account_list = [acc.strip() for acc in accounts[0].split(',')]
                    else:
                        account_list = accounts
                
                multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_list)
                
                # Pre-fetch account aliases before closing connection
                account_aliases = {}
                for snapshot in multi_portfolio.snapshots:
                    try:
                        alias = portfolio_service.get_account_alias(snapshot.account_id)
                        account_aliases[snapshot.account_id] = alias
                    except Exception as e:
                        logger.debug(f"Could not get account alias for {snapshot.account_id}: {e}")
                        account_aliases[snapshot.account_id] = None
            
            if not multi_portfolio.snapshots:
                console.print("[yellow]⚠️ No portfolio data downloaded[/yellow]")
                raise typer.Exit(0)

        # Export results to holdings table format (outside with block to ensure connection is closed)
        from .utils.holdings_exporter import export_holdings_table
        output_path = export_holdings_table(
            multi_portfolio=multi_portfolio,
            output_filename=output_filename,
            account_aliases=account_aliases  # Pass pre-fetched aliases instead of service
        )
        
        # Show summary
        combined_summary = multi_portfolio.get_combined_summary()
        
        console.print(f"[green]✅ Holdings table download completed:[/green]")
        console.print(f"  • Accounts processed: {combined_summary['total_accounts']}")
        console.print(f"  • Total positions (including zero): {sum(len(s.positions) for s in multi_portfolio.snapshots)}")
        console.print(f"  • Active positions (non-zero): {combined_summary['total_positions']}")
        console.print(f"  • Total portfolio value: ${combined_summary['total_portfolio_value']:,.2f}")
        console.print(f"  • Output: [cyan]{output_path}[/cyan]")
        
        # Show per-account summary
        console.print(f"\n[bold blue]📋 Per-Account Holdings Summary:[/bold blue]")
        for snapshot in multi_portfolio.snapshots:
            account_summary = snapshot.get_positions_summary()
            total_positions = len(snapshot.positions)
            active_positions = len([p for p in snapshot.positions if p.position != 0])
            
            console.print(f"  • Account {snapshot.account_id}: "
                         f"{total_positions} total positions ({active_positions} active), "
                         f"${account_summary['total_value']:,.2f} total value")

    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during holdings download")
        raise typer.Exit(1)


@app.command()
def run_daily_update(
    accounts: Optional[List[str]] = typer.Option(
        None, "--accounts", "-a",
        help="Specific account IDs to process (comma-separated). If not provided, processes all accounts."
    ),
    skip_email: bool = typer.Option(
        False, "--skip-email",
        help="Skip sending email notification"
    ),
    skip_sharepoint: bool = typer.Option(
        False, "--skip-sharepoint", 
        help="Skip uploading to SharePoint"
    ),
):
    """Run automated daily portfolio update with SharePoint and email integration."""
    
    console.print("[bold blue]🤖 Starting automated daily portfolio update[/bold blue]")
    
    try:
        # Parse account list if provided
        account_list = None
        if accounts:
            if len(accounts) == 1 and ',' in accounts[0]:
                account_list = [acc.strip() for acc in accounts[0].split(',')]
            else:
                account_list = accounts
        
        # Run the automated update
        with console.status("[bold green]Running automated portfolio update..."):
            result = automated_portfolio_service.run_daily_portfolio_update(
                account_ids=account_list,
                send_email=not skip_email,
                upload_to_sharepoint=not skip_sharepoint
            )
        
        # Display results
        if result['success']:
            console.print(f"[green]✅ Daily portfolio update completed successfully![/green]")
            console.print(f"  • Duration: {result['duration_seconds']:.1f} seconds")
            console.print(f"  • Accounts processed: {result['accounts_processed']}")
            console.print(f"  • Total portfolio value: ${result['total_portfolio_value']:,.2f}")
            console.print(f"  • SharePoint uploaded: {'✅' if result['sharepoint_uploaded'] else '❌'}")
            console.print(f"  • Email sent: {'✅' if result['email_sent'] else '❌'}")
            
            if result['files_created']:
                console.print(f"\n[bold blue]📄 Files created:[/bold blue]")
                for file_path in result['files_created']:
                    console.print(f"  • {file_path}")
            
            # Show operation log
            console.print(f"\n[bold blue]📋 Operation Log:[/bold blue]")
            for log_entry in result['operation_log']:
                console.print(f"  {log_entry}")
        
        else:
            console.print(f"[red]❌ Daily portfolio update failed![/red]")
            
            if result['errors']:
                console.print(f"\n[bold red]Errors:[/bold red]")
                for error in result['errors']:
                    console.print(f"  • {error}")
            
            if result['operation_log']:
                console.print(f"\n[bold blue]📋 Operation Log:[/bold blue]")
                for log_entry in result['operation_log']:
                    console.print(f"  {log_entry}")
            
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Unexpected error in automated update: {e}[/red]")
        logger.exception("Unexpected error during automated update")
        raise typer.Exit(1)


@app.command()
def test_integrations():
    """Test all integrations (SharePoint, Email, IBKR) for automated services."""
    
    console.print("[bold blue]🔧 Testing system integrations[/bold blue]")
    
    try:
        with console.status("[bold green]Testing integrations..."):
            results = automated_portfolio_service.test_integrations()
        
        # Create results table
        table = Table(title="Integration Test Results")
        table.add_column("Service", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="yellow")
        
        # SharePoint
        sharepoint_status = "✅ Available" if results['sharepoint']['available'] else "❌ Unavailable"
        sharepoint_details = ""
        if results['sharepoint']['available']:
            info = results['sharepoint'].get('info', {})
            sharepoint_details = f"Files: {info.get('total_files', 'N/A')}, Size: {info.get('project_size_mb', 'N/A')} MB"
        elif results['sharepoint']['error']:
            sharepoint_details = f"Error: {results['sharepoint']['error']}"
        
        table.add_row("SharePoint/OneDrive", sharepoint_status, sharepoint_details)
        
        # Email
        email_status = "✅ Available" if results['email']['available'] else "❌ Unavailable"
        email_details = results['email']['error'] if results['email']['error'] else "SMTP connection successful"
        table.add_row("Email (Office 365)", email_status, email_details)
        
        # IBKR
        ibkr_status = "✅ Connected" if results['ibkr']['available'] else "❌ Disconnected"
        ibkr_details = results['ibkr']['error'] if results['ibkr']['error'] else "API connection successful"
        table.add_row("IBKR Gateway", ibkr_status, ibkr_details)
        
        console.print(table)
        
        # Overall status
        all_available = all(result['available'] for result in results.values())
        if all_available:
            console.print("\n[green]🎉 All integrations are working correctly![/green]")
            console.print("[green]The automated daily update system is ready to use.[/green]")
        else:
            console.print("\n[yellow]⚠️ Some integrations have issues.[/yellow]")
            console.print("[yellow]Please resolve the issues before running automated updates.[/yellow]")
    
    except Exception as e:
        console.print(f"[red]❌ Integration test failed: {e}[/red]")
        logger.exception("Integration test error")
        raise typer.Exit(1)


@app.command()
def update_market_data(
    force_update: bool = typer.Option(
        False, "--force",
        help="Force update even if cache is fresh"
    ),
    max_age_hours: float = typer.Option(
        24.0, "--max-age",
        help="Maximum cache age in hours before update (default: 24)"
    ),
    send_notification: bool = typer.Option(
        True, "--notify/--no-notify",
        help="Send email notification after update"
    ),
):
    """Update market data prices for all universe symbols."""
    
    console.print("[bold blue]📊 Starting market data update[/bold blue]")
    
    try:
        # Set role to Trade Assistant for market data operations
        from .auth.permissions import set_current_user_role, UserRole
        set_current_user_role(UserRole.TRADE_ASSISTANT)
        
        with console.status("[bold green]Updating market data from IBKR..."):
            result = market_data_service.update_universe_prices(
                force_update=force_update,
                max_age_hours=max_age_hours
            )
        
        if result['success']:
            if result['cache_was_fresh']:
                console.print(f"[green]✅ Cache was fresh - no update needed[/green]")
                console.print(f"  • Cached symbols: {result['symbols_updated']}")
                console.print(f"  • Data date: {result['data_date']}")
            else:
                console.print(f"[green]✅ Market data update completed![/green]")
                console.print(f"  • Symbols updated: {result['symbols_updated']}")
                console.print(f"  • Symbols failed: {result['symbols_failed']}")
                console.print(f"  • Duration: {result['duration_seconds']:.1f} seconds")
                console.print(f"  • Data date: {result['data_date']}")
            
            # Send notification if requested and not just a cache check
            if send_notification and not result['cache_was_fresh']:
                console.print("\n[bold blue]📧 Sending notification...[/bold blue]")
                notification_sent = market_data_service.send_market_data_notification(result)
                
                if notification_sent:
                    console.print("[green]✅ Notification sent successfully[/green]")
                else:
                    console.print("[yellow]⚠️ Failed to send notification[/yellow]")
        else:
            console.print(f"[red]❌ Market data update failed![/red]")
            
            if result['errors']:
                console.print(f"\n[bold red]Errors:[/bold red]")
                for error in result['errors']:
                    console.print(f"  • {error}")
            
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]❌ Unexpected error in market data update: {e}[/red]")
        logger.exception("Unexpected error during market data update")
        raise typer.Exit(1)


@app.command()
def market_data_status():
    """Show market data cache status and information."""
    
    console.print("[bold blue]📊 Market Data Cache Status[/bold blue]")
    
    try:
        cache_info = market_data_service.get_cache_status()
        
        # Create status table
        table = Table(title="Cache Information")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Cache File Exists", "✅ Yes" if cache_info['cache_file_exists'] else "❌ No")
        table.add_row("Cached Symbols", str(cache_info['cached_symbols']))
        table.add_row("Last Update", cache_info.get('last_update', 'Never'))
        table.add_row("Data Date", cache_info.get('data_date', 'Unknown'))
        
        age_hours = cache_info.get('cache_age_hours')
        if age_hours is not None:
            age_status = "Fresh" if age_hours <= 24 else "Stale"
            table.add_row("Cache Age", f"{age_hours:.1f} hours ({age_status})")
        else:
            table.add_row("Cache Age", "Unknown")
        
        table.add_row("Update Source", cache_info.get('update_source', 'Unknown'))
        
        console.print(table)
        
        # Show cache freshness status
        is_fresh = market_data_service.cache.is_cache_fresh(24.0)
        if is_fresh:
            console.print("\n[green]🎉 Cache is fresh and ready to use![/green]")
        else:
            console.print("\n[yellow]⚠️ Cache is stale - consider updating[/yellow]")
            console.print("[yellow]Run: simple-order update-market-data[/yellow]")
    
    except Exception as e:
        console.print(f"[red]❌ Failed to get cache status: {e}[/red]")
        logger.exception("Cache status error")
        raise typer.Exit(1)


@app.command()
def download_positions_cached(
    accounts: Optional[List[str]] = typer.Option(
        None, "--accounts", "-a",
        help="Specific account IDs to download (comma-separated). If not provided, downloads all accounts."
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output Excel filename. Default: auto-generated with timestamp"
    ),
    # IB connection overrides
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Download portfolio positions using cached market data (faster, offline-capable)."""
    
    console.print("[bold blue]📊 Starting portfolio download with cached prices[/bold blue]")
    
    try:
        # Check cache status first
        cache_info = market_data_service.get_cache_status()
        
        if cache_info['cached_symbols'] == 0:
            console.print("[red]❌ No cached market data available![/red]")
            console.print("[yellow]Please run 'simple-order update-market-data' first[/yellow]")
            raise typer.Exit(1)
        
        if not market_data_service.cache.is_cache_fresh(48.0):  # Allow 48h for cached mode
            console.print("[yellow]⚠️ Warning: Cached data is stale (>48h old)[/yellow]")
            console.print(f"[yellow]Last update: {cache_info.get('last_update', 'Unknown')}[/yellow]")
        
        # Load app configuration
        app_config = config_loader.load_app_config()
        
        # Get IB connection settings with overrides
        ib_settings = app_config.ib_settings
        host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
        port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
        client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

        # Execute download with IB connection (using cached prices)
        with IBConnector(host=host, port=port, client_id=client_id) as connector:
            provider = IBProvider(connector)
            portfolio_service = PortfolioService(provider, use_cached_prices=True)  # Enable cached prices

            with console.status("[bold green]Downloading portfolio positions (cached prices)..."):
                # Parse account list if provided
                account_list = None
                if accounts:
                    if len(accounts) == 1 and ',' in accounts[0]:
                        account_list = [acc.strip() for acc in accounts[0].split(',')]
                    else:
                        account_list = accounts
                
                multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_list)
            
            if not multi_portfolio.snapshots:
                console.print("[yellow]⚠️ No portfolio data downloaded[/yellow]")
                raise typer.Exit(0)

            # Export results to IBKR standard Excel format
            output_path = export_ibkr_portfolio_report(
                multi_portfolio=multi_portfolio,
                output_filename=output_filename,
                include_metadata=True
            )
            
            # Show summary
            combined_summary = multi_portfolio.get_combined_summary()
            
            console.print(f"[green]✅ Portfolio download completed (cached prices)![/green]")
            console.print(f"  • Accounts processed: {combined_summary['total_accounts']}")
            console.print(f"  • Total positions: {combined_summary['total_positions']}")
            console.print(f"  • Total portfolio value: ${combined_summary['total_portfolio_value']:,.2f}")
            console.print(f"  • Price data date: {cache_info.get('data_date', 'Unknown')}")
            console.print(f"  • Output: [cyan]{output_path}[/cyan]")
    
    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during cached portfolio download")
        raise typer.Exit(1)


@app.command()
def generate_orders(
    account_id: str = typer.Argument(..., help="Account ID to generate orders for"),
    portfolio_id: str = typer.Argument(..., help="Model portfolio ID (e.g., B301 for GTAA)"),
    order_type: str = typer.Option(
        "rebalance", "--type", "-t",
        help="Order type: rebalance, deposit, withdrawal"
    ),
    amount: Optional[float] = typer.Option(
        None, "--amount", "-a",
        help="Amount for deposit/withdrawal or target amount for rebalancing"
    ),
    proportional: bool = typer.Option(
        True, "--proportional/--largest-first",
        help="For withdrawal: sell proportionally (default) or largest positions first"
    ),
    min_trade_amount: float = typer.Option(
        100.0, "--min-trade",
        help="Minimum trade amount for rebalancing (default: $100)"
    ),
    model_portfolio_path: Optional[str] = typer.Option(
        None, "--mp-path",
        help="Path to MP_Master.csv file. Default: ./data/model_portfolios/MP_Master.csv"
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output CSV filename for orders. Default: auto-generated"
    ),
    # IB connection parameters (only needed for rebalancing)
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Generate trading orders based on model portfolio."""
    
    console.print(f"[bold blue]📝 Generating {order_type} orders for account {account_id}[/bold blue]")

    try:
        # Validate order type
        if order_type not in ['rebalance', 'deposit', 'withdrawal']:
            console.print(f"[red]❌ Invalid order type: {order_type}. Must be: rebalance, deposit, withdrawal[/red]")
            raise typer.Exit(1)
        
        # Validate required amount parameter
        if amount is None:
            console.print(f"[red]❌ Amount parameter is required for {order_type} orders[/red]")
            raise typer.Exit(1)
        
        amount_decimal = Decimal(str(amount))
        
        # Load model portfolios
        mp_path = model_portfolio_path or "./data/model_portfolios/MP_Master.csv"
        try:
            order_service = OrderService.load_model_portfolios_from_csv(mp_path)
            console.print(f"[green]✓[/green] Loaded model portfolios from: {mp_path}")
        except Exception as e:
            console.print(f"[red]❌ Failed to load model portfolios: {e}[/red]")
            raise typer.Exit(1)
        
        # Validate portfolio exists
        if portfolio_id not in order_service.model_portfolio_manager.list_portfolio_ids():
            available = order_service.model_portfolio_manager.list_portfolio_ids()
            console.print(f"[red]❌ Portfolio ID '{portfolio_id}' not found. Available: {', '.join(available)}[/red]")
            raise typer.Exit(1)
        
        order_batch = None
        
        if order_type == "deposit":
            # Generate deposit orders (no IB connection needed)
            console.print(f"Generating deposit orders for ${amount_decimal:,.2f}")
            order_batch = order_service.generate_deposit_orders(
                account_id=account_id,
                portfolio_id=portfolio_id,
                deposit_amount=amount_decimal
            )
            
        elif order_type == "withdrawal" or order_type == "rebalance":
            # Need IB connection to get current positions
            app_config = config_loader.load_app_config()
            ib_settings = app_config.ib_settings
            host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
            port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
            client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

            with IBConnector(host=host, port=port, client_id=client_id) as connector:
                provider = IBProvider(connector)
                portfolio_service = PortfolioService(provider)

                with console.status("[bold green]Getting current portfolio positions..."):
                    current_snapshot = portfolio_service.download_account_portfolio(account_id)
                
                console.print(f"[green]✓[/green] Retrieved current positions: {len(current_snapshot.positions)} positions")
                
                if order_type == "withdrawal":
                    console.print(f"Generating withdrawal orders for ${amount_decimal:,.2f}")
                    order_batch = order_service.generate_withdrawal_orders(
                        account_id=account_id,
                        current_snapshot=current_snapshot,
                        withdrawal_amount=amount_decimal,
                        proportional=proportional
                    )
                    
                elif order_type == "rebalance":
                    console.print(f"Generating rebalancing orders to ${amount_decimal:,.2f} target")
                    order_batch = order_service.generate_rebalancing_orders(
                        account_id=account_id,
                        portfolio_id=portfolio_id,
                        current_snapshot=current_snapshot,
                        target_amount=amount_decimal,
                        min_trade_amount=Decimal(str(min_trade_amount))
                    )
        
        if not order_batch or not order_batch.orders:
            console.print("[yellow]⚠️ No orders generated[/yellow]")
            raise typer.Exit(0)
        
        # Save orders to CSV
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"orders_{order_type}_{account_id}_{portfolio_id}_{timestamp}.csv"
        
        if not output_filename.endswith('.csv'):
            output_filename += '.csv'
        
        # Get output directory
        app_config = config_loader.load_app_config()
        from pathlib import Path
        output_dir = Path(app_config.app.get("directories", {}).get("output_dir", "./data/output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        
        order_batch.save_to_csv(output_path)
        
        # Show summary
        summary = order_batch.get_summary()
        
        console.print(f"[green]✅ Order generation completed:[/green]")
        console.print(f"  • Order type: {order_type}")
        console.print(f"  • Account: {account_id}")
        console.print(f"  • Portfolio: {portfolio_id}")
        console.print(f"  • Total orders: {summary['total_orders']}")
        console.print(f"  • Buy orders: {summary['buy_orders']} (${summary['total_buy_amount']:,.2f})")
        console.print(f"  • Sell orders: {summary['sell_orders']} (${summary['total_sell_amount']:,.2f})")
        console.print(f"  • Net amount: ${summary['net_amount']:,.2f}")
        console.print(f"  • Output: [cyan]{output_path}[/cyan]")
        
        # Show individual orders
        if len(order_batch.orders) <= 10:  # Show details if not too many orders
            console.print(f"\n[bold blue]📋 Order Details:[/bold blue]")
            for i, order in enumerate(order_batch.orders, 1):
                console.print(f"  {i}. {order.action} {order.symbol}: ${order.amount:,.2f} ({order.notes})")

    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during order generation")
        raise typer.Exit(1)


@app.command()
def list_portfolios(
    model_portfolio_path: Optional[str] = typer.Option(
        None, "--mp-path",
        help="Path to MP_Master.csv file. Default: ./data/model_portfolios/MP_Master.csv"
    ),
):
    """List all available model portfolios."""
    
    console.print("[bold blue]📋 Available Model Portfolios[/bold blue]")
    
    try:
        # Load model portfolios
        mp_path = model_portfolio_path or "./data/model_portfolios/MP_Master.csv"
        manager = ModelPortfolioManager.load_from_csv(mp_path)
        
        table = Table(title="Model Portfolios")
        table.add_column("Portfolio ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Holdings", justify="right", style="magenta")
        table.add_column("Total Weight", justify="right", style="yellow")
        table.add_column("Effective Date", style="blue")
        
        for portfolio_id in manager.list_portfolio_ids():
            portfolio = manager.get_portfolio(portfolio_id)
            holdings_str = ", ".join([h.get_instrument_identifier() for h in portfolio.holdings])
            
            table.add_row(
                portfolio_id,
                portfolio.bucket_name,
                f"{len(portfolio.holdings)} ({holdings_str})",
                f"{float(portfolio.total_weight or 0):.2f}%",
                portfolio.effective_date
            )
        
        console.print(table)
        console.print(f"\n[green]✓[/green] Loaded from: {mp_path}")
        
    except Exception as e:
        console.print(f"[red]❌ Error loading model portfolios: {e}[/red]")
        raise typer.Exit(1)


# ========================================
# Scheduler Commands (Singapore Timezone)
# ========================================

@app.command("start-scheduler")
def start_scheduler():
    """Start the Singapore timezone scheduler daemon for automated daily updates."""
    
    console.print("[bold blue]🚀 Starting Portfolio Management Scheduler[/bold blue]")
    
    try:
        import asyncio
        from .services.scheduler_service import SchedulerService
        from .config import Config
        
        # Load configuration
        config = Config()
        
        # Create and run scheduler
        scheduler_service = SchedulerService(config)
        
        console.print("[green]✓[/green] Scheduler configuration loaded")
        console.print(f"[green]✓[/green] Timezone: Asia/Singapore")
        console.print(f"[green]✓[/green] Market data update: {config.app['scheduling']['market_data_update']} SGT daily")
        console.print(f"[green]✓[/green] Portfolio update: {config.app['scheduling']['portfolio_update']} SGT daily")
        
        # Run scheduler
        asyncio.run(scheduler_service.run_forever())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Scheduler stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Scheduler error: {e}[/red]")
        logger.exception("Unexpected error in scheduler")
        raise typer.Exit(1)


@app.command("scheduler-status")
def scheduler_status():
    """Check the status of scheduled tasks and next run times."""
    
    console.print("[bold blue]📊 Scheduler Status[/bold blue]")
    
    try:
        import asyncio
        from .services.scheduler_service import SchedulerService, SchedulerContext
        from .config import Config
        import pytz
        from datetime import datetime
        
        # Load configuration
        config = Config()
        singapore_tz = pytz.timezone('Asia/Singapore')
        current_time = datetime.now(singapore_tz)
        
        console.print(f"[green]✓[/green] Current time (SGT): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Show configuration
        console.print(f"\n[bold blue]📅 Schedule Configuration:[/bold blue]")
        console.print(f"  • Market Data Update: {config.app['scheduling']['market_data_update']} SGT daily")
        console.print(f"  • Portfolio Update: {config.app['scheduling']['portfolio_update']} SGT daily")
        console.print(f"  • Timezone: Asia/Singapore")
        
        # Try to get scheduler status (if running)
        async def get_status():
            try:
                async with SchedulerContext(config) as scheduler:
                    return scheduler.get_status()
            except Exception:
                return None
        
        status = asyncio.run(get_status())
        
        if status and status.get('running'):
            console.print(f"\n[green]🟢 Scheduler Status: RUNNING[/green]")
            
            if status.get('jobs'):
                table = Table(title="Scheduled Jobs")
                table.add_column("Job Name", style="cyan")
                table.add_column("Next Run", style="green")
                table.add_column("Trigger", style="yellow")
                
                for job in status['jobs']:
                    table.add_row(
                        job['name'],
                        job['next_run_time'] or 'Not scheduled',
                        job['trigger']
                    )
                
                console.print(table)
        else:
            console.print(f"\n[red]🔴 Scheduler Status: NOT RUNNING[/red]")
            console.print("Use 'start-scheduler' command to start the scheduler daemon.")
        
    except Exception as e:
        console.print(f"[red]❌ Error checking scheduler status: {e}[/red]")
        raise typer.Exit(1)


@app.command("test-scheduler")
def test_scheduler():
    """Test the scheduler service by running a quick validation of all components."""
    
    console.print("[bold blue]🧪 Testing Scheduler Service Components[/bold blue]")
    
    try:
        import asyncio
        from .services.scheduler_service import SchedulerService
        from .config import Config
        
        async def run_tests():
            # Load configuration
            config = Config()
            
            console.print("[green]✓[/green] Configuration loaded successfully")
            
            # Create scheduler service (don't start)
            scheduler_service = SchedulerService(config)
            
            console.print("[green]✓[/green] Scheduler service initialized")
            
            # Test configuration parsing
            try:
                market_data_time = scheduler_service._parse_time_config(
                    config.app['scheduling']['market_data_update']
                )
                portfolio_time = scheduler_service._parse_time_config(
                    config.app['scheduling']['portfolio_update']
                )
                
                console.print(f"[green]✓[/green] Schedule times parsed: Market data {market_data_time}, Portfolio {portfolio_time}")
            except Exception as e:
                console.print(f"[red]❌ Time parsing failed: {e}[/red]")
                return False
            
            # Test service dependencies
            try:
                # Check automation service
                automation_service = scheduler_service.automation_service
                console.print("[green]✓[/green] Automation service accessible")
                
                # Check market data service  
                market_data_service = scheduler_service.market_data_service
                console.print("[green]✓[/green] Market data service accessible")
                
                # Check email service
                email_service = scheduler_service.email_service
                console.print("[green]✓[/green] Email service accessible")
                
            except Exception as e:
                console.print(f"[red]❌ Service dependency failed: {e}[/red]")
                return False
            
            # Test timezone
            try:
                from datetime import datetime
                current_time = datetime.now(scheduler_service.singapore_tz)
                console.print(f"[green]✓[/green] Singapore timezone working: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            except Exception as e:
                console.print(f"[red]❌ Timezone test failed: {e}[/red]")
                return False
            
            return True
        
        success = asyncio.run(run_tests())
        
        if success:
            console.print(f"\n[green]✅ All scheduler tests passed![/green]")
            console.print("The scheduler service is ready to run.")
        else:
            console.print(f"\n[red]❌ Some scheduler tests failed![/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]❌ Scheduler test error: {e}[/red]")
        logger.exception("Unexpected error during scheduler test")
        raise typer.Exit(1)


@app.command("run-daily-update")
def run_daily_update(
    use_cached_prices: bool = typer.Option(
        True, "--use-cached/--live-prices",
        help="Use cached market data prices (default) or fetch live prices"
    )
):
    """Run the complete daily portfolio update workflow manually (same as scheduled version)."""
    
    console.print("[bold blue]🔄 Running Daily Portfolio Update Workflow[/bold blue]")
    
    try:
        import asyncio
        from .services.automation_service import AutomationService
        from .config import Config
        from datetime import datetime
        import pytz
        
        # Load configuration
        config = Config()
        singapore_tz = pytz.timezone('Asia/Singapore')
        start_time = datetime.now(singapore_tz)
        
        console.print(f"Start time (SGT): {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        console.print(f"Using cached prices: {'Yes' if use_cached_prices else 'No (live prices)'}")
        
        async def run_workflow():
            # Create automation service
            automation_service = AutomationService(config)
            
            with console.status("[bold green]Running portfolio update workflow..."):
                # Run the full daily update
                results = await automation_service.run_daily_portfolio_update(
                    use_cached_prices=use_cached_prices
                )
            
            return results
        
        # Run the workflow
        results = asyncio.run(run_workflow())
        
        end_time = datetime.now(singapore_tz)
        duration = (end_time - start_time).total_seconds()
        
        console.print(f"\n[green]✅ Daily portfolio update completed in {duration:.1f} seconds[/green]")
        
        # Show results
        console.print(f"\n[bold blue]📋 Results:[/bold blue]")
        for key, value in results.items():
            if hasattr(value, 'name'):  # Path object
                console.print(f"  • {key}: {value.name}")
            else:
                console.print(f"  • {key}: {value}")
        
    except Exception as e:
        end_time = datetime.now(singapore_tz)
        duration = (end_time - start_time).total_seconds()
        
        console.print(f"[red]❌ Daily update failed after {duration:.1f} seconds: {e}[/red]")
        logger.exception("Unexpected error during daily update")
        raise typer.Exit(1)


@app.command("update-market-data")
def update_market_data():
    """Update market data cache using Trade Assistant role (same as scheduled version)."""
    
    console.print("[bold blue]📊 Updating Market Data Cache[/bold blue]")
    
    try:
        import asyncio
        from .services.market_data_service import MarketDataService
        from .auth.permissions import UserRole
        from .config import Config
        from datetime import datetime
        import pytz
        
        # Load configuration
        config = Config()
        singapore_tz = pytz.timezone('Asia/Singapore')
        start_time = datetime.now(singapore_tz)
        
        console.print(f"Start time (SGT): {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        console.print(f"Role: Trade Assistant")
        
        def update_cache():
            # Set role to Trade Assistant for market data operations
            from .auth.permissions import set_current_user_role
            set_current_user_role(UserRole.TRADE_ASSISTANT)
            
            # Create market data service
            market_data_service = MarketDataService()
            
            with console.status("[bold green]Updating market data cache..."):
                # Update universe prices using Trade Assistant role
                market_data_service.update_universe_prices(force_update=False, max_age_hours=24.0)
            
            with console.status("[bold green]Exporting market data report..."):
                # Export market data report
                output_file = market_data_service.export_market_data_report()
            
            return output_file
        
        # Run the update
        output_file = update_cache()
        
        end_time = datetime.now(singapore_tz)
        duration = (end_time - start_time).total_seconds()
        
        console.print(f"\n[green]✅ Market data update completed in {duration:.1f} seconds[/green]")
        console.print(f"  • Output file: [cyan]{output_file.name if output_file else 'N/A'}[/cyan]")
        
    except Exception as e:
        end_time = datetime.now(singapore_tz)
        duration = (end_time - start_time).total_seconds()
        
        console.print(f"[red]❌ Market data update failed after {duration:.1f} seconds: {e}[/red]")
        logger.exception("Unexpected error during market data update")
        raise typer.Exit(1)


@app.command("market-data-status")
def market_data_status():
    """Check market data cache status and freshness."""
    
    console.print("[bold blue]📊 Market Data Cache Status[/bold blue]")
    
    try:
        from .services.market_data_service import MarketDataService
        from .config import Config
        from datetime import datetime
        import pytz
        
        # Load configuration
        config = Config()
        singapore_tz = pytz.timezone('Asia/Singapore')
        current_time = datetime.now(singapore_tz)
        
        console.print(f"Current time (SGT): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Create market data service
        market_data_service = MarketDataService()
        
        # Get cache status
        status = market_data_service.get_cache_status()
        
        console.print(f"\n[bold blue]💾 Cache Status:[/bold blue]")
        console.print(f"  • Cache directory: {status['cache_dir']}")
        console.print(f"  • Cache exists: {'Yes' if status['cache_exists'] else 'No'}")
        console.print(f"  • Cache file count: {status['cache_file_count']}")
        console.print(f"  • Last updated: {status['last_updated'] or 'Never'}")
        console.print(f"  • Is fresh: {'Yes' if status['is_fresh'] else 'No'}")
        console.print(f"  • Age (hours): {status['age_hours']:.1f}" if status['age_hours'] is not None else "  • Age: N/A")
        
        # Show freshness status
        if status['is_fresh']:
            console.print(f"\n[green]✅ Market data cache is FRESH[/green]")
        else:
            console.print(f"\n[yellow]⚠️ Market data cache is STALE[/yellow]")
            console.print("Consider running 'update-market-data' to refresh the cache.")
        
    except Exception as e:
        console.print(f"[red]❌ Error checking market data status: {e}[/red]")
        raise typer.Exit(1)


@app.command("download-positions-cached")
def download_positions_cached(
    accounts: Optional[List[str]] = typer.Option(
        None, "--accounts", "-a",
        help="Specific account IDs to download (comma-separated). If not provided, downloads all accounts."
    ),
    output_filename: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output Excel filename. Default: auto-generated with timestamp"
    ),
    # IB connection overrides
    ib_host: Optional[str] = typer.Option(None, "--ib-host", help="IB host override"),
    ib_port: Optional[int] = typer.Option(None, "--ib-port", help="IB port override"),
    ib_client_id: Optional[int] = typer.Option(None, "--ib-client-id", help="IB client ID override"),
):
    """Download portfolio positions using cached market data prices (offline operation)."""
    
    console.print("[bold blue]📊 Downloading Portfolio Positions (Cached Prices)[/bold blue]")
    
    try:
        # Load app configuration
        app_config = config_loader.load_app_config()
        
        # Get IB connection settings with overrides
        ib_settings = app_config.ib_settings
        host = ib_host if ib_host is not None else ib_settings.get("host", "127.0.0.1")
        port = ib_port if ib_port is not None else ib_settings.get("port", 7497)
        client_id = ib_client_id if ib_client_id is not None else ib_settings.get("client_id", 1)

        # Execute download with IB connection but using cached prices
        with IBConnector(host=host, port=port, client_id=client_id) as connector:
            provider = IBProvider(connector)
            portfolio_service = PortfolioService(provider)

            with console.status("[bold green]Downloading portfolio positions with cached prices..."):
                # Parse account list if provided
                account_list = None
                if accounts:
                    if len(accounts) == 1 and ',' in accounts[0]:
                        # Handle comma-separated string
                        account_list = [acc.strip() for acc in accounts[0].split(',')]
                    else:
                        account_list = accounts
                
                # Download using cached prices
                multi_portfolio = portfolio_service.download_all_portfolios(
                    account_ids=account_list, 
                    use_cached_prices=True  # Key difference from regular download
                )
            
            if not multi_portfolio.snapshots:
                console.print("[yellow]⚠️ No portfolio data downloaded[/yellow]")
                raise typer.Exit(0)

            # Export results to IBKR standard Excel format
            output_path = export_ibkr_portfolio_report(
                multi_portfolio=multi_portfolio,
                output_filename=output_filename,
                include_metadata=True
            )
            
            # Show summary
            combined_summary = multi_portfolio.get_combined_summary()
            
            console.print(f"[green]✅ Cached portfolio download completed:[/green]")
            console.print(f"  • Accounts processed: {combined_summary['total_accounts']}")
            console.print(f"  • Total positions: {combined_summary['total_positions']}")
            console.print(f"  • Total portfolio value: ${combined_summary['total_portfolio_value']:,.2f}")
            console.print(f"  • Price source: CACHED DATA")
            console.print(f"  • Output: [cyan]{output_path}[/cyan]")

    except ConnectionError as e:
        console.print(f"[red]❌ Connection Error: {e}[/red]")
        raise typer.Exit(1)
    except SimpleOrderManagementPlatformError as e:
        console.print(f"[red]❌ Platform Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during cached positions download")
        raise typer.Exit(1)


@app.command("test-integrations")
def test_integrations():
    """Test all system integrations (IBKR, SharePoint, Email, Market Data)."""
    
    console.print("[bold blue]🧪 Testing System Integrations[/bold blue]")
    
    try:
        import asyncio
        from .services.automation_service import AutomationService
        from .config import Config
        
        async def run_integration_tests():
            # Load configuration
            config = Config()
            
            console.print("[green]✓[/green] Configuration loaded")
            
            # Create automation service
            automation_service = AutomationService(config)
            
            console.print("[green]✓[/green] Automation service initialized")
            
            # Run integration tests
            with console.status("[bold green]Running integration tests..."):
                results = await automation_service.test_integrations()
            
            return results
        
        # Run tests
        results = asyncio.run(run_integration_tests())
        
        console.print(f"\n[bold blue]📋 Integration Test Results:[/bold blue]")
        
        all_passed = True
        for service_name, result in results.items():
            if result.get('success', False):
                console.print(f"  ✅ {service_name}: PASSED")
                if result.get('details'):
                    console.print(f"      {result['details']}")
            else:
                console.print(f"  ❌ {service_name}: FAILED")
                if result.get('error'):
                    console.print(f"      Error: {result['error']}")
                all_passed = False
        
        if all_passed:
            console.print(f"\n[green]✅ All integration tests passed![/green]")
        else:
            console.print(f"\n[red]❌ Some integration tests failed![/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]❌ Integration test error: {e}[/red]")
        logger.exception("Unexpected error during integration tests")
        raise typer.Exit(1)


# =====================================
# MODEL PORTFOLIO MANAGEMENT COMMANDS
# =====================================

@app.command(name="list-model-portfolios")
def list_model_portfolios():
    """📊 List all available model portfolios."""
    try:
        from .services.model_portfolio_service import ModelPortfolioService
        
        console.print("📊 [bold blue]Listing Model Portfolios[/bold blue]")
        
        mp_service = ModelPortfolioService()
        portfolios = mp_service.list_model_portfolios()
        
        if not portfolios:
            console.print("❌ No model portfolios found")
            return
        
        table = Table(title="Available Model Portfolios")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Holdings", style="green")
        
        for mp_name in portfolios:
            mp = mp_service.get_model_portfolio(mp_name)
            if mp:
                holdings_str = ", ".join([f"{h.symbol} ({h.target_weight:.2%})" for h in mp.holdings])
                table.add_row(mp.name, mp.description or "N/A", holdings_str)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error listing model portfolios: {e}[/red]")
        logger.exception("Error listing model portfolios")
        raise typer.Exit(1)


@app.command(name="show-model-portfolio")
def show_model_portfolio(
    name: str = typer.Argument(..., help="Model portfolio name")
):
    """📋 Show detailed information about a model portfolio."""
    try:
        from .services.model_portfolio_service import ModelPortfolioService
        
        console.print(f"📋 [bold blue]Model Portfolio: {name}[/bold blue]")
        
        mp_service = ModelPortfolioService()
        mp = mp_service.get_model_portfolio(name)
        
        if not mp:
            console.print(f"❌ Model portfolio '{name}' not found")
            return
        
        # Portfolio info
        console.print(f"\n[bold]Name:[/bold] {mp.name}")
        console.print(f"[bold]Description:[/bold] {mp.description or 'N/A'}")
        console.print(f"[bold]Created:[/bold] {mp.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"[bold]Updated:[/bold] {mp.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Holdings table
        table = Table(title="Portfolio Holdings")
        table.add_column("Symbol", style="cyan")
        table.add_column("Target Weight", style="green", justify="right")
        table.add_column("Security Type", style="white")
        table.add_column("Exchange", style="white")
        table.add_column("Currency", style="yellow")
        
        total_weight = Decimal('0')
        for holding in mp.holdings:
            table.add_row(
                holding.symbol,
                f"{holding.target_weight:.4f} ({holding.target_weight:.2%})",
                holding.security_type,
                holding.exchange,
                holding.currency
            )
            total_weight += holding.target_weight
        
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{total_weight:.4f} ({total_weight:.2%})[/bold]",
            "", "", ""
        )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error showing model portfolio: {e}[/red]")
        logger.exception("Error showing model portfolio")
        raise typer.Exit(1)


@app.command(name="assign-account")
def assign_account_to_model_portfolio(
    account_id: str = typer.Argument(..., help="Account ID"),
    model_portfolio: str = typer.Argument(..., help="Model portfolio name")
):
    """🔗 Assign an account to a model portfolio."""
    try:
        from .services.model_portfolio_service import ModelPortfolioService
        
        console.print(f"🔗 [bold blue]Assigning Account to Model Portfolio[/bold blue]")
        
        mp_service = ModelPortfolioService()
        mp_service.assign_account_to_model_portfolio(account_id, model_portfolio)
        
        console.print(f"✅ Successfully assigned account '{account_id}' to model portfolio '{model_portfolio}'")
        
    except Exception as e:
        console.print(f"[red]❌ Error assigning account: {e}[/red]")
        logger.exception("Error assigning account to model portfolio")
        raise typer.Exit(1)


@app.command(name="calculate-rebalancing")
def calculate_rebalancing(
    accounts: Optional[List[str]] = typer.Option(None, "--accounts", "-a", help="Specific accounts to analyze"),
    model_portfolio: Optional[str] = typer.Option(None, "--model-portfolio", "-m", help="Model portfolio name"),
    host: Optional[str] = typer.Option(None, "--host", help="IB Gateway host"),
    port: Optional[int] = typer.Option(None, "--port", help="IB Gateway port"),
    client_id: Optional[int] = typer.Option(None, "--client-id", help="IB client ID")
):
    """⚖️ Calculate rebalancing requirements for accounts."""
    try:
        from .services.model_portfolio_service import ModelPortfolioService
        
        console.print("⚖️ [bold blue]Calculating Rebalancing Requirements[/bold blue]")
        
        # Load configuration
        app_config = config_loader.get_config("app")
        host, port, client_id, alternative_ports = get_ib_connection_params(app_config, host, port, client_id)
        
        # Get current portfolio data
        with IBConnector(host=host, port=port, client_id=client_id, alternative_ports=alternative_ports) as connector:
            provider = IBProvider(connector)
            portfolio_service = PortfolioService(provider)
            
            if accounts:
                account_list = accounts
            else:
                account_list = portfolio_service.get_all_accounts()
            
            multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_list)
        
        # Calculate rebalancing
        mp_service = ModelPortfolioService()
        calculations = mp_service.calculate_multi_account_rebalancing(multi_portfolio, model_portfolio)
        
        if not calculations:
            console.print("❌ No rebalancing calculations generated")
            return
        
        # Display results
        for calc in calculations:
            console.print(f"\n[bold cyan]Account: {calc.account_id}[/bold cyan]")
            console.print(f"Model Portfolio: {calc.model_portfolio_name}")
            console.print(f"Total Value: ${calc.total_portfolio_value:,.2f}")
            
            # Rebalancing table
            table = Table(title=f"Rebalancing Analysis - {calc.account_id}")
            table.add_column("Symbol", style="cyan")
            table.add_column("Current Weight", style="white", justify="right")
            table.add_column("Target Weight", style="green", justify="right")
            table.add_column("Difference", style="yellow", justify="right")
            table.add_column("Current Shares", style="white", justify="right")
            table.add_column("Required Action", style="red", justify="right")
            
            for symbol in calc.target_weights.keys():
                current_weight = calc.current_weights.get(symbol, Decimal('0'))
                target_weight = calc.target_weights[symbol]
                weight_diff = calc.weight_differences[symbol]
                current_shares = calc.current_positions.get(symbol, Decimal('0'))
                shares_action = calc.orders_required.get(symbol, Decimal('0'))
                
                # Color code the difference
                if abs(weight_diff) > Decimal('0.01'):  # > 1%
                    diff_color = "red" if weight_diff < 0 else "green"
                    diff_str = f"[{diff_color}]{weight_diff:+.2%}[/{diff_color}]"
                else:
                    diff_str = f"{weight_diff:+.2%}"
                
                action_str = f"{shares_action:+.2f}" if shares_action != 0 else "No action"
                
                table.add_row(
                    symbol,
                    f"{current_weight:.2%}",
                    f"{target_weight:.2%}",
                    diff_str,
                    f"{current_shares:.2f}",
                    action_str
                )
            
            console.print(table)
            
            if calc.needs_rebalancing():
                console.print("📈 [yellow]Rebalancing recommended[/yellow]")
            else:
                console.print("✅ [green]Portfolio is balanced[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Error calculating rebalancing: {e}[/red]")
        logger.exception("Error calculating rebalancing")
        raise typer.Exit(1)


@app.command(name="generate-orders")
def generate_rebalancing_orders(
    output_file: str = typer.Argument(..., help="Output CSV file path"),
    accounts: Optional[List[str]] = typer.Option(None, "--accounts", "-a", help="Specific accounts to rebalance"),
    model_portfolio: Optional[str] = typer.Option(None, "--model-portfolio", "-m", help="Model portfolio name"),
    day: Optional[int] = typer.Option(None, "--day", help="Generate orders for specific day (1 or 2)"),
    host: Optional[str] = typer.Option(None, "--host", help="IB Gateway host"),
    port: Optional[int] = typer.Option(None, "--port", help="IB Gateway port"),
    client_id: Optional[int] = typer.Option(None, "--client-id", help="IB client ID")
):
    """📋 Generate rebalancing orders and export to IBKR CSV format."""
    try:
        from .services.model_portfolio_service import ModelPortfolioService
        
        console.print("📋 [bold blue]Generating Rebalancing Orders[/bold blue]")
        
        # Load configuration
        app_config = config_loader.get_config("app")
        host, port, client_id, alternative_ports = get_ib_connection_params(app_config, host, port, client_id)
        
        # Get current portfolio data
        with IBConnector(host=host, port=port, client_id=client_id, alternative_ports=alternative_ports) as connector:
            provider = IBProvider(connector)
            portfolio_service = PortfolioService(provider)
            
            if accounts:
                account_list = accounts
            else:
                account_list = portfolio_service.get_all_accounts()
            
            multi_portfolio = portfolio_service.download_all_portfolios(account_ids=account_list)
        
        # Calculate rebalancing and generate orders
        mp_service = ModelPortfolioService()
        calculations = mp_service.calculate_multi_account_rebalancing(multi_portfolio, model_portfolio)
        
        if not calculations:
            console.print("❌ No rebalancing calculations generated")
            return
        
        # Generate rebalancing plan
        rebalance_plan = mp_service.generate_rebalance_plan(calculations)
        
        # Export orders
        mp_service.export_orders_to_ibkr_csv(rebalance_plan, output_file, day)
        
        # Display summary
        console.print(f"\n[bold green]✅ Orders Generated Successfully[/bold green]")
        console.print(f"Output file: {output_file}")
        console.print(f"Model Portfolio: {rebalance_plan.model_portfolio_name}")
        console.print(f"Execution Date: {rebalance_plan.execution_date.strftime('%Y-%m-%d')}")
        console.print(f"Basket Tag: {rebalance_plan.basket_tag}")
        
        if day == 1:
            console.print(f"Day 1 Orders: {len(rebalance_plan.day_1_orders)}")
        elif day == 2:
            console.print(f"Day 2 Orders: {len(rebalance_plan.day_2_orders)}")
        else:
            console.print(f"Day 1 Orders: {len(rebalance_plan.day_1_orders)}")
            console.print(f"Day 2 Orders: {len(rebalance_plan.day_2_orders)}")
            console.print(f"Total Orders: {len(rebalance_plan.get_all_orders())}")
        
        # Show order summary table
        orders_to_show = []
        if day == 1:
            orders_to_show = rebalance_plan.day_1_orders
        elif day == 2:
            orders_to_show = rebalance_plan.day_2_orders
        else:
            orders_to_show = rebalance_plan.get_all_orders()
        
        if orders_to_show:
            table = Table(title="Generated Orders")
            table.add_column("Account", style="cyan")
            table.add_column("Symbol", style="white")
            table.add_column("Action", style="green")
            table.add_column("Quantity", style="yellow", justify="right")
            table.add_column("Order Type", style="white")
            table.add_column("Day", style="blue")
            
            for order in orders_to_show:
                table.add_row(
                    order.account_id,
                    order.symbol,
                    order.action.value,
                    f"{order.quantity:.6f}".rstrip('0').rstrip('.'),
                    order.order_type.value,
                    str(order.rebalance_day)
                )
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error generating orders: {e}[/red]")
        logger.exception("Error generating rebalancing orders")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
