from typing import List, Dict, Any, Optional
import random
import json
import datetime
from agents import function_tool
from pydantic import BaseModel, Field

# Define models for tool inputs and outputs

# Networking tool models
class CheckNsgRulesInput(BaseModel):
    resource_group: str = Field(..., description="Azure resource group name")
    nsg_name: Optional[str] = Field(None, description="Optional NSG name to check specific NSG")

class NsgRule(BaseModel):
    name: str
    priority: int
    direction: str
    access: str
    protocol: str
    source_address_prefix: str
    source_port_range: str
    destination_address_prefix: str
    destination_port_range: str
    is_blocking: bool = False

class CheckNsgRulesOutput(BaseModel):
    rules: List[NsgRule]
    blocking_rules: List[NsgRule]
    has_issues: bool

class CheckDnsInput(BaseModel):
    hostname: str = Field(..., description="Hostname to resolve")
    dns_server: Optional[str] = Field(None, description="Optional DNS server to use")

class DnsResolutionResult(BaseModel):
    resolved_ip: Optional[str] = None
    status: str
    latency_ms: int
    success: bool

class CheckDnsOutput(BaseModel):
    hostname: str
    resolution_results: List[DnsResolutionResult]
    has_issues: bool

# Availability tool models
class GetResourceUsageInput(BaseModel):
    container_app_name: str = Field(..., description="Container App name")
    resource_group: str = Field(..., description="Azure resource group name")
    minutes: int = Field(20, description="Number of minutes to look back")

class TimeSeriesPoint(BaseModel):
    timestamp: str
    value: float

class ResourceUsageOutput(BaseModel):
    app_name: str
    metric_name: str
    unit: str
    time_series: List[TimeSeriesPoint]
    average: float
    max: float
    min: float
    has_issues: bool

class GetLogsInput(BaseModel):
    container_app_name: str = Field(..., description="Container App name")
    resource_group: str = Field(..., description="Azure resource group name")
    minutes: int = Field(20, description="Number of minutes to look back")
    error_only: bool = Field(True, description="Only return error logs")

class LogSummary(BaseModel):
    total_logs: int
    error_count: int
    warning_count: int
    error_categories: Dict[str, int]
    sample_errors: List[str]
    has_issues: bool

# Networking diagnostic tools
@function_tool
def check_nsg_rules(resource_group: str, nsg_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Check NSG rules for potential blocking issues.
    
    Args:
        resource_group: Azure resource group name
        nsg_name: Optional NSG name to check specific NSG
        
    Returns:
        Dictionary with NSG rules and analysis
    """
    # Generate mock NSG rules
    all_rules = []
    blocking_rules = []
    
    # Common ports for web applications
    common_ports = ["80", "443", "8080", "3000-3010"]
    
    # Create some normal rules
    normal_rules = [
        NsgRule(
            name="AllowHTTPS",
            priority=100,
            direction="Inbound",
            access="Allow",
            protocol="TCP",
            source_address_prefix="*",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range="443"
        ),
        NsgRule(
            name="AllowHTTP",
            priority=110,
            direction="Inbound",
            access="Allow",
            protocol="TCP",
            source_address_prefix="*",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range="80"
        ),
        NsgRule(
            name="AllowSSH",
            priority=120,
            direction="Inbound",
            access="Allow",
            protocol="TCP",
            source_address_prefix="10.0.0.0/24",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range="22"
        )
    ]
    all_rules.extend(normal_rules)
    
    # Add some blocking rules (50% chance)
    if random.random() > 0.5:
        # Create a blocking rule for a common port
        blocked_port = random.choice(common_ports)
        blocking_rule = NsgRule(
            name="DenyCustomPort",
            priority=90,  # Higher priority (lower number)
            direction="Inbound",
            access="Deny",
            protocol="TCP",
            source_address_prefix="*",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range=blocked_port,
            is_blocking=True
        )
        all_rules.append(blocking_rule)
        blocking_rules.append(blocking_rule)
    
    # 30% chance to add a specific subnet blocking rule
    if random.random() > 0.7:
        subnet_blocking_rule = NsgRule(
            name="DenySubnet",
            priority=150,
            direction="Inbound",
            access="Deny",
            protocol="*",
            source_address_prefix="192.168.0.0/24",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range="*",
            is_blocking=True
        )
        all_rules.append(subnet_blocking_rule)
        blocking_rules.append(subnet_blocking_rule)
    
    # Add default deny rule at the end
    default_rule = NsgRule(
        name="DenyAll",
        priority=4096,
        direction="Inbound",
        access="Deny",
        protocol="*",
        source_address_prefix="*",
        source_port_range="*",
        destination_address_prefix="*",
        destination_port_range="*"
    )
    all_rules.append(default_rule)
    
    return CheckNsgRulesOutput(
        rules=all_rules,
        blocking_rules=blocking_rules,
        has_issues=len(blocking_rules) > 0
    ).dict()

@function_tool
def check_dns(hostname: str, dns_server: Optional[str] = None) -> Dict[str, Any]:
    """
    Check DNS resolution for a hostname.
    
    Args:
        hostname: Hostname to resolve
        dns_server: Optional DNS server to use
        
    Returns:
        Dictionary with DNS resolution results
    """
    # Generate mock DNS resolution results
    dns_servers = dns_server.split(",") if dns_server else ["Primary DNS", "Secondary DNS"]
    
    # 30% chance of DNS issues
    has_dns_issues = random.random() < 0.3
    
    results = []
    for server in dns_servers:
        if has_dns_issues and server == dns_servers[0]:  # Only primary DNS has issues
            result = DnsResolutionResult(
                resolved_ip=None,
                status="Failed to resolve" if random.random() < 0.5 else "Timeout",
                latency_ms=random.randint(500, 2000),
                success=False
            )
        else:
            # Generate a random IP address
            ip_parts = [str(random.randint(1, 255)) for _ in range(4)]
            ip = ".".join(ip_parts)
            
            result = DnsResolutionResult(
                resolved_ip=ip,
                status="Resolved successfully",
                latency_ms=random.randint(5, 100),
                success=True
            )
        
        results.append(result)
    
    return CheckDnsOutput(
        hostname=hostname,
        resolution_results=results,
        has_issues=has_dns_issues
    ).dict()

# Availability diagnostic tools
@function_tool
def get_cpu_usage(container_app_name: str, resource_group: str, minutes: int = 20) -> Dict[str, Any]:
    """
    Get CPU usage for a Container App.
    
    Args:
        container_app_name: Container App name
        resource_group: Azure resource group name
        minutes: Number of minutes to look back
        
    Returns:
        Dictionary with CPU usage time series
    """
    return _generate_resource_usage(container_app_name, "CPU", "percentage", minutes, high_chance=0.4)

@function_tool
def get_memory_usage(container_app_name: str, resource_group: str, minutes: int = 20) -> Dict[str, Any]:
    """
    Get memory usage for a Container App.
    
    Args:
        container_app_name: Container App name
        resource_group: Azure resource group name
        minutes: Number of minutes to look back
        
    Returns:
        Dictionary with memory usage time series
    """
    return _generate_resource_usage(container_app_name, "Memory", "MB", minutes, high_chance=0.3)

def _generate_resource_usage(app_name: str, metric_name: str, unit: str, minutes: int, high_chance: float = 0.3) -> Dict[str, Any]:
    """Helper function to generate resource usage data"""
    # Generate mock time series data
    now = datetime.datetime.now()
    time_series = []
    
    # Determine if we should show high usage
    high_usage = random.random() < high_chance
    
    # Set base and peak values based on the metric
    if metric_name == "CPU":
        base_value = 30.0
        peak_value = 95.0 if high_usage else 60.0
    else:  # Memory
        base_value = 500.0
        peak_value = 1800.0 if high_usage else 1000.0
    
    values = []
    
    # Generate time series with potential spike
    for i in range(minutes):
        timestamp = now - datetime.timedelta(minutes=minutes-i)
        
        # Create a spike in the middle if high usage
        if high_usage and minutes // 3 < i < 2 * minutes // 3:
            # Ramp up and down around the spike
            distance_from_center = abs(i - minutes // 2)
            severity = 1 - (distance_from_center / (minutes // 6))
            value = base_value + (peak_value - base_value) * max(0, severity)
        else:
            # Normal variation
            variation = random.uniform(-0.1, 0.1)
            value = base_value * (1 + variation)
        
        values.append(value)
        
        time_series.append(TimeSeriesPoint(
            timestamp=timestamp.isoformat(),
            value=round(value, 2)
        ))
    
    # Calculate statistics
    avg_value = sum(values) / len(values)
    max_value = max(values)
    min_value = min(values)
    
    # Determine if this is an issue based on the metric
    has_issues = False
    if metric_name == "CPU" and max_value > 90:
        has_issues = True
    elif metric_name == "Memory" and max_value > 1500:
        has_issues = True
    
    return ResourceUsageOutput(
        app_name=app_name,
        metric_name=metric_name,
        unit=unit,
        time_series=time_series,
        average=round(avg_value, 2),
        max=round(max_value, 2),
        min=round(min_value, 2),
        has_issues=has_issues
    ).dict()

@function_tool
def get_logs(container_app_name: str, resource_group: str, minutes: int = 20, error_only: bool = True) -> Dict[str, Any]:
    """
    Get logs for a Container App.
    
    Args:
        container_app_name: Container App name
        resource_group: Azure resource group name
        minutes: Number of minutes to look back
        error_only: Only return error logs
        
    Returns:
        Dictionary with log summary
    """
    # Define possible error types
    error_types = [
        "Connection timeout",
        "Database connection failed",
        "Out of memory",
        "Permission denied",
        "Image pull failure",
        "API request failed",
        "Certificate validation error",
        "Service unavailable"
    ]
    
    # 40% chance of serious errors
    has_serious_errors = random.random() < 0.4
    
    # Generate mock log summary
    total_logs = random.randint(500, 2000)
    
    # Select error categories and counts
    if has_serious_errors:
        # More serious errors
        error_count = random.randint(50, 200)
        warning_count = random.randint(100, 300)
        
        # Select 2-3 types of errors
        selected_errors = random.sample(error_types, k=random.randint(2, 3))
        
        # Image pull failure is common for container apps
        if "Image pull failure" not in selected_errors and random.random() < 0.7:
            selected_errors[0] = "Image pull failure"
    else:
        # Fewer errors
        error_count = random.randint(5, 30)
        warning_count = random.randint(20, 80)
        
        # Select 1-2 types of errors
        selected_errors = random.sample(error_types, k=random.randint(1, 2))
    
    # Distribute error counts
    error_categories = {}
    remaining_errors = error_count
    
    for i, error_type in enumerate(selected_errors):
        if i == len(selected_errors) - 1:
            # Last category gets all remaining errors
            error_categories[error_type] = remaining_errors
        else:
            # Allocate a portion of errors
            count = random.randint(max(1, remaining_errors // 10), remaining_errors // 2)
            error_categories[error_type] = count
            remaining_errors -= count
    
    # Generate sample error messages
    sample_errors = []
    
    for error_type, count in error_categories.items():
        if error_type == "Connection timeout":
            sample_errors.append(f"ERROR: Connection timeout after 30s when connecting to external API endpoint")
        elif error_type == "Database connection failed":
            sample_errors.append(f"ERROR: Failed to connect to database: Connection refused (0x5)")
        elif error_type == "Out of memory":
            sample_errors.append(f"ERROR: Container terminated due to OOM: Limit: 2048Mi")
        elif error_type == "Permission denied":
            sample_errors.append(f"ERROR: Permission denied when accessing blob storage account")
        elif error_type == "Image pull failure":
            sample_errors.append(f"ERROR: Failed to pull image 'myregistry.azurecr.io/myapp:latest': unauthorized: authentication required")
        elif error_type == "API request failed":
            sample_errors.append(f"ERROR: API request to dependency service failed with status code 503")
        elif error_type == "Certificate validation error":
            sample_errors.append(f"ERROR: Certificate validation failed: certificate has expired")
        elif error_type == "Service unavailable":
            sample_errors.append(f"ERROR: Dependency service unavailable: connection refused")
    
    return LogSummary(
        total_logs=total_logs,
        error_count=error_count,
        warning_count=warning_count,
        error_categories=error_categories,
        sample_errors=sample_errors,
        has_issues=has_serious_errors
    ).dict()