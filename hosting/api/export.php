<?php
declare(strict_types=1);

// Da caricare nella STESSA cartella di config.php sul server
// (es. cuoredinapoli.net/database/export.php).
//
// Espone in JSON il contenuto della tabella, protetto da una API key
// condivisa (config.php -> 'api_key'), da passare come header:
//   X-Api-Key: <valore>
//
// Il programma Python locale la chiama per scaricare le entry.

// <-- ADATTA al nome reale della tabella (vista in phpMyAdmin)
const TABLE_NAME = 'messaggi';

header('Content-Type: application/json; charset=utf-8');

$config = require __DIR__ . '/config.php';

$providedKey = $_SERVER['HTTP_X_API_KEY'] ?? '';
if ($providedKey === '' || !hash_equals((string) $config['api_key'], $providedKey)) {
    http_response_code(401);
    echo json_encode(['error' => 'unauthorized']);
    exit;
}

$mysqli = new mysqli(
    $config['db_host'],
    $config['db_user'],
    $config['db_pass'],
    $config['db_name']
);

if ($mysqli->connect_errno) {
    http_response_code(500);
    echo json_encode(['error' => 'db_connection_failed']);
    exit;
}

$table = $mysqli->real_escape_string(TABLE_NAME);
$result = $mysqli->query(
    "SELECT id, text, created_at, status, ip, likes FROM `{$table}` ORDER BY id"
);

if ($result === false) {
    http_response_code(500);
    echo json_encode(['error' => 'query_failed']);
    $mysqli->close();
    exit;
}

$rows = [];
while ($row = $result->fetch_assoc()) {
    $rows[] = $row;
}

echo json_encode($rows);
$mysqli->close();
