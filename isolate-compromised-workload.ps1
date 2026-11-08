$namespace = "zt-integration"
$label = "security-status=compromised"

Write-Host "Checking for compromised workloads..."

$pods = kubectl get pods -n $namespace -l $label -o name

if ($pods) {
    Write-Host "Compromised workload detected!"
    Write-Host $pods

    kubectl apply -f .\compromised-isolation.yaml

    Write-Host "Isolation policy applied successfully."
}
else {
    Write-Host "No compromised workload detected."
}