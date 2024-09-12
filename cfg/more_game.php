<?php
// 定义静态配置
$config = [
    'app_name' => 'My App',
    'version' => '1.0.0',
    'api_url' => 'https://api.example.com',
    'features' => [
        'feature1' => true,
        'feature2' => false,
        'feature3' => true
    ]
];

// 设置响应头为 JSON
header('Content-Type: application/json');

// 输出 JSON 格式的配置
echo json_encode($config, JSON_PRETTY_PRINT);
