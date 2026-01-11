# 检查localhost和网络配置

Write-Host "=== 网络配置信息 ===" -ForegroundColor Green
Write-Host ""

Write-Host "1. localhost 地址:" -ForegroundColor Yellow
Write-Host "   - IPv4: 127.0.0.1"
Write-Host "   - IPv6: ::1"
Write-Host "   - 域名: localhost"
Write-Host ""

Write-Host "2. 本机IP地址（局域网）:" -ForegroundColor Yellow
$ipconfig = ipconfig | Select-String "IPv4"
$ipconfig | ForEach-Object {
    $ip = $_ -replace ".*IPv4.*: ", ""
    Write-Host "   - $ip" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "3. 访问Web界面的地址:" -ForegroundColor Yellow
Write-Host "   本机访问: http://localhost:8000" -ForegroundColor Green
Write-Host "   本机访问: http://127.0.0.1:8000" -ForegroundColor Green
$ipconfig | ForEach-Object {
    $ip = $_ -replace ".*IPv4.*: ", ""
    Write-Host "   局域网访问: http://$ip`:8000" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "4. 测试端口是否开放:" -ForegroundColor Yellow
$port = 8000
$connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue
if ($connection.TcpTestSucceeded) {
    Write-Host "   端口 $port 已开放，服务正在运行" -ForegroundColor Green
} else {
    Write-Host "   端口 $port 未开放，请先启动Web服务器" -ForegroundColor Yellow
    Write-Host "   启动命令: python -m src.main web" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "=== 提示 ===" -ForegroundColor Green
Write-Host "- 使用 localhost 或 127.0.0.1 只能在本机访问" -ForegroundColor White
Write-Host "- 使用本机IP地址可以让局域网内其他设备访问" -ForegroundColor White
Write-Host "- 如果使用 0.0.0.0 启动服务器，可以通过以上所有地址访问" -ForegroundColor White
