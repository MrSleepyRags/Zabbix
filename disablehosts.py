#!/usr/bin/env python3
"""
Zabbix API Script to Disable Hosts with Agent Unavailable for >11 Days
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys

class ZabbixAPI:
    def __init__(self, url, username, password):
        self.url = url.rstrip('/') + '/api_jsonrpc.php'
        self.username = username
        self.password = password
        self.auth_token = None
        self.session = requests.Session()
        
    def authenticate(self):
        """Authenticate with Zabbix API and get auth token"""
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "username": self.username,
                "password": self.password
            },
            "id": 1
        }
        
        try:
            response = self.session.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"Authentication failed: {result['error']['data']}")
                
            self.auth_token = result['result']
            print("✓ Successfully authenticated with Zabbix API")
            return True
            
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return False
    
    def api_call(self, method, params=None):
        """Make a generic API call"""
        if not self.auth_token:
            raise Exception("Not authenticated. Call authenticate() first.")
            
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "auth": self.auth_token,
            "id": 1
        }
        
        try:
            response = self.session.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"API call failed: {result['error']['data']}")
                
            return result['result']
            
        except Exception as e:
            print(f"✗ API call failed for {method}: {e}")
            raise
    
    def get_problem_hosts(self, days_threshold=11):
        """Get hosts with Zabbix agent problems older than threshold"""
        threshold_time = int((datetime.now() - timedelta(days=days_threshold)).timestamp())

        # Get problems related to Zabbix agent availability
        problems = self.api_call("problem.get", {
            "output": ["eventid", "name", "clock", "severity", "objectid"],
            "sortfield": "eventid",  # Only "eventid" is allowed
            "sortorder": "DESC",
            "time_from": 0,
            "time_till": int(datetime.now().timestamp()),
            "search": {
                "name": "Zabbix agent is not available"
            }
        })

        # Filter for problems older than threshold
        old_problems = []
        for problem in problems:
            if int(problem['clock']) <= threshold_time:
                old_problems.append(problem)

        # Extract unique hosts with problems using event.get
        problem_hosts = {}
        for problem in old_problems:
            eventid = problem['eventid']
            # Use event.get to get host info for this problem
            events = self.api_call("event.get", {
                "output": ["eventid"],
                "selectHosts": ["hostid", "host", "name", "status"],
                "eventids": eventid
            })
            for event in events:
                for host in event.get('hosts', []):
                    # Only consider enabled hosts (status 0 = enabled, 1 = disabled)
                    if host['status'] == '0':
                        host_id = host['hostid']
                        if host_id not in problem_hosts:
                            problem_hosts[host_id] = {
                                'hostid': host_id,
                                'host': host['host'],
                                'name': host['name'],
                                'problem_since': datetime.fromtimestamp(int(problem['clock'])),
                                'days_ago': (datetime.now() - datetime.fromtimestamp(int(problem['clock']))).days
                            }

        return list(problem_hosts.values())
    
    def disable_host(self, host_id):
        """Disable a specific host"""
        return self.api_call("host.update", {
            "hostid": host_id,
            "status": 1  # 1 = disabled, 0 = enabled
        })
    
    def logout(self):
        """Logout from Zabbix API"""
        if self.auth_token:
            try:
                self.api_call("user.logout")
                print("✓ Logged out from Zabbix API")
            except:
                pass  # Ignore logout errors

def main():
    # Configuration - Update these values
    ZABBIX_URL = "IT GOES HERE"  # Change this
    USERNAME = "IT GOES HERE"    # Change this
    PASSWORD = "IT GOES HERE"    # Change this
    DAYS_THRESHOLD = 11
    DRY_RUN = True  # Set to False to actually disable hosts
    
    print("Zabbix Host Disabler Script")
    print("=" * 40)
    print(f"Target: {ZABBIX_URL}")
    print(f"Threshold: {DAYS_THRESHOLD} days")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print("=" * 40)
    
    # Initialize API connection
    zapi = ZabbixAPI(ZABBIX_URL, USERNAME, PASSWORD)
    
    try:
        # Authenticate
        if not zapi.authenticate():
            sys.exit(1)
        
        # Get hosts with agent problems
        print(f"\n🔍 Searching for hosts with agent problems > {DAYS_THRESHOLD} days...")
        problem_hosts = zapi.get_problem_hosts(DAYS_THRESHOLD)
        
        if not problem_hosts:
            print("✓ No hosts found with agent problems older than threshold")
            return
        
        print(f"\n📋 Found {len(problem_hosts)} hosts with agent issues:")
        print("-" * 80)
        print(f"{'Host ID':<10} {'Hostname':<25} {'Display Name':<25} {'Days Ago':<10}")
        print("-" * 80)
        
        for host in problem_hosts:
            print(f"{host['hostid']:<10} {host['host']:<25} {host['name']:<25} {host['days_ago']:<10}")
        
        if DRY_RUN:
            print(f"\n⚠️  DRY RUN MODE - No hosts will be disabled")
            print("Set DRY_RUN = False to actually disable these hosts")
        else:
            # Confirm action
            print(f"\n⚠️  About to disable {len(problem_hosts)} hosts!")
            confirm = input("Are you sure? Type 'yes' to continue: ")
            
            if confirm.lower() != 'yes':
                print("Operation cancelled")
                return
            
            # Disable hosts
            print("\n🔧 Disabling hosts...")
            success_count = 0
            error_count = 0
            
            for host in problem_hosts:
                try:
                    zapi.disable_host(host['hostid'])
                    print(f"✓ Disabled: {host['host']} ({host['name']})")
                    success_count += 1
                    time.sleep(0.1)  # Small delay to avoid API overload
                    
                except Exception as e:
                    print(f"✗ Failed to disable {host['host']}: {e}")
                    error_count += 1
            
            print(f"\n📊 Summary:")
            print(f"   Successfully disabled: {success_count}")
            print(f"   Errors: {error_count}")
            print(f"   Total processed: {len(problem_hosts)}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user")
    except Exception as e:
        print(f"\n✗ Script failed: {e}")
        sys.exit(1)
    finally:
        zapi.logout()

if __name__ == "__main__":
    main()
