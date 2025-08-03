#!/usr/bin/env python3
"""
Deployment Status Check Script
Verifies that the trading platform is deployment-ready
"""

import os
import json
from pathlib import Path
from datetime import datetime

def check_netlify_files():
    """Check if Netlify deployment files are ready"""
    required_files = [
        'index.html',
        'dashboard.html', 
        'app.js',
        'netlify.toml',
        '_redirects'
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    return len(missing) == 0, missing

def check_security():
    """Check if security credentials are properly configured"""
    issues = []
    
    # Check app.yaml for exposed secrets
    app_yaml = Path('app.yaml')
    if app_yaml.exists():
        content = app_yaml.read_text()
        if 'PK3FA0MFPOWADZVIJBF7' in content:
            issues.append("API keys still exposed in app.yaml")
        if 'iemytkjQt5yxRPBoSe62DpyoQ5b2oXBunV8e1BiA' in content:
            issues.append("Secret keys still exposed in app.yaml")
    
    # Check for .env.example
    if not Path('.env.example').exists():
        issues.append("Missing .env.example file")
    
    return len(issues) == 0, issues

def check_backend_readiness():
    """Check if backend is deployment-ready"""
    required_files = [
        'app_platform_api.py',
        'requirements.txt',
        'Dockerfile',
        'health_check.py'
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    return len(missing) == 0, missing

def generate_deployment_report():
    """Generate comprehensive deployment report"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "deployment_status": "ready",
        "checks": {},
        "recommendations": [],
        "next_steps": []
    }
    
    # Frontend check
    frontend_ready, missing_frontend = check_netlify_files()
    report["checks"]["frontend"] = {
        "status": "pass" if frontend_ready else "fail",
        "missing_files": missing_frontend
    }
    
    # Security check
    security_ok, security_issues = check_security()
    report["checks"]["security"] = {
        "status": "pass" if security_ok else "fail",
        "issues": security_issues
    }
    
    # Backend check
    backend_ready, missing_backend = check_backend_readiness()
    report["checks"]["backend"] = {
        "status": "pass" if backend_ready else "fail",
        "missing_files": missing_backend
    }
    
    # Overall status
    all_ready = frontend_ready and security_ok and backend_ready
    if not all_ready:
        report["deployment_status"] = "not_ready"
    
    # Recommendations
    if not frontend_ready:
        report["recommendations"].append("Complete Netlify file preparation")
    if not security_ok:
        report["recommendations"].append("Fix security credential exposure")
    if not backend_ready:
        report["recommendations"].append("Complete backend deployment files")
    
    # Next steps
    if all_ready:
        report["next_steps"] = [
            "1. Set environment variables in Digital Ocean App Platform",
            "2. Deploy frontend to Netlify",
            "3. Configure domain DNS settings",
            "4. Test end-to-end connectivity",
            "5. Monitor health checks"
        ]
    else:
        report["next_steps"] = [
            "Fix failing checks above",
            "Re-run deployment readiness check"
        ]
    
    return report

def main():
    """Main deployment status check"""
    print("HutzTrades Deployment Status Check")
    print("=" * 50)
    
    # Generate report
    report = generate_deployment_report()
    
    # Display results
    print(f"Status: {report['deployment_status'].upper()}")
    print(f"Timestamp: {report['timestamp']}")
    print()
    
    # Check results
    for check_name, check_data in report["checks"].items():
        status = check_data["status"]
        print(f"{check_name.capitalize()}: {status.upper()}")
        
        if status == "fail":
            if "missing_files" in check_data and check_data["missing_files"]:
                print(f"  Missing files: {check_data['missing_files']}")
            if "issues" in check_data and check_data["issues"]:
                print(f"  Issues: {check_data['issues']}")
        print()
    
    # Recommendations
    if report["recommendations"]:
        print("Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")
        print()
    
    # Next steps
    print("Next Steps:")
    for step in report["next_steps"]:
        print(f"  {step}")
    print()
    
    # Save report
    report_file = Path("logs/deployment_status.json")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved to: {report_file}")
    
    # Exit with appropriate code
    if report["deployment_status"] == "ready":
        print("\n[SUCCESS] Platform is ready for deployment!")
        return 0
    else:
        print("\n[WARNING] Platform needs fixes before deployment")
        return 1

if __name__ == "__main__":
    exit(main())