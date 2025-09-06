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
from .core.orchestrator import DataOrchestrator
from .providers.ib import IBProvider
from .models.base import InstrumentType
from .utils.exporters import export_multi_asset_results, export_portfolio_snapshots
from .utils.exceptions import SimpleOrderManagementPlatformError, ConnectionError
from .services.portfolio_service import PortfolioService
from .services.order_service import OrderService
from .models.model_portfolio import ModelPortfolioManager

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
        port = ib_port if ib_port is not None else ib_settings.get("port", 4001)
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
            port = ib_port if ib_port is not None else ib_settings.get("port", 4001)
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
