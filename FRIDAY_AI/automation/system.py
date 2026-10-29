import platform
import psutil
from backend.result import Result

def metrics():
    mem=psutil.virtual_memory(); battery=psutil.sensors_battery()
    stats=psutil.net_if_stats(); addrs=psutil.net_if_addrs()
    interfaces=[]
    for name,s in stats.items():
        if s.isup and any(a.address not in ('127.0.0.1','::1') and getattr(a.family,'name','') in ('AF_INET','AF_INET6') for a in addrs.get(name,[])):
            interfaces.append(name)
    from datetime import datetime
    return {'local_time':datetime.now().astimezone().isoformat(), 'platform':platform.system(), 'platform_release':platform.release(), 'cpu_percent':psutil.cpu_percent(interval=None), 'ram_percent':mem.percent, 'ram_used_gb':round(mem.used/(1024**3),1), 'ram_total_gb':round(mem.total/(1024**3),1), 'battery_percent':round(battery.percent) if battery else None, 'battery_plugged':battery.power_plugged if battery else None, 'network_interface_up':bool(interfaces),'network_interfaces':interfaces[:5]}

def status_tool(_args=None, expected=None):
    return Result(True,True,'Live local system metrics collected.',metrics())
