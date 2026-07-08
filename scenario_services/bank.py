SERVICE_NAME = "VulnBank"  
SERVICE_SLUG = "vulnbank"
DESCRIPTION = "A deliberately vulnerable banking app with SQLi, XSS, broken auth, file upload, command injection, LFI, IDOR, and privilege escalation — covers Phases 4–7."
FLAG = "FLAG{vulnbank_pwned_all_in_one}"

DOCKERFILE = r"""FROM php:8.1-apache
RUN docker-php-ext-install pdo pdo_sqlite
RUN a2enmod rewrite
COPY *.php /var/www/html/
COPY style.css /var/www/html/
RUN mkdir -p /var/www/html/uploads && chmod 777 /var/www/html/uploads
RUN mkdir -p /var/www/html/logs && chmod 777 /var/www/html/logs
RUN echo "{{FLAG}}" > /var/www/html/flag.txt
RUN echo "[LOG] System initialized" > /var/www/html/logs/app.log
"""

LOGIN_PHP = """<?php
session_start();
$db = new PDO('sqlite:/tmp/bank.db');
$db->exec("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, full_name TEXT, role TEXT, avatar TEXT)");
$db->exec("INSERT OR IGNORE INTO users VALUES (1,'admin','admin123','Admin User','admin','')");
$db->exec("INSERT OR IGNORE INTO users VALUES (2,'alice','alice123','Alice Johnson','user','')");
$db->exec("INSERT OR IGNORE INTO users VALUES (3,'bob','bob123','Bob Smith','user','')");
$db->exec("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, user_id INTEGER, account_no TEXT, balance REAL)");
$db->exec("INSERT OR IGNORE INTO accounts VALUES (1,1,'ACC-0001',999999)");
$db->exec("INSERT OR IGNORE INTO accounts VALUES (2,2,'ACC-0002',5000)");
$db->exec("INSERT OR IGNORE INTO accounts VALUES (3,3,'ACC-0003',3200)");
$db->exec("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)");
$db->exec("CREATE TABLE IF NOT EXISTS transfers (id INTEGER PRIMARY KEY AUTOINCREMENT, from_acc TEXT, to_acc TEXT, amount REAL, memo TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)");

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = $_POST['username'] ?? '';
    $pass = $_POST['password'] ?? '';
    $sql = "SELECT * FROM users WHERE username='$user' AND password='$pass'";
    $result = $db->query($sql);
    if ($result && $row = $result->fetch(PDO::FETCH_ASSOC)) {
        $_SESSION['user_id'] = $row['id'];
        $_SESSION['username'] = $row['username'];
        $_SESSION['role'] = $row['role'];
        $_SESSION['full_name'] = $row['full_name'];
        header("Location: dashboard.php");
        exit;
    }
    $error = "Invalid login.";
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>VulnBank</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card login-card">
<h1>VulnBank</h1>
<p class="subtitle">Secure Online Banking</p>
<?php if ($error): ?><p class="error"><?= $error ?></p><?php endif; ?>
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Sign In</button>
</form>
<p class="hint">Try: <strong>' OR 1=1 --</strong> or brute force common creds</p>
<p class="hint">Known users: admin, alice, bob (passwords: admin123, alice123, bob123)</p>
</div></div></body></html>"""

DASHBOARD_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/bank.db');
$uid = $_SESSION['user_id'];
$user = $db->query("SELECT * FROM users WHERE id=$uid")->fetch(PDO::FETCH_ASSOC);
$accts = $db->query("SELECT * FROM accounts WHERE user_id=$uid")->fetchAll(PDO::FETCH_ASSOC);
$flag = file_get_contents('/var/www/html/flag.txt');
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Dashboard</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>Welcome, <?= htmlspecialchars($user['full_name']) ?></h1>
<p>Username: <?= htmlspecialchars($_SESSION['username']) ?> | Role: <?= htmlspecialchars($_SESSION['role']) ?></p>
</div>
<div class="card">
<h2>Your Accounts</h2>
<?php foreach ($accts as $a): ?>
<p>Account: <?= htmlspecialchars($a['account_no']) ?> — Balance: $<?= number_format($a['balance'], 2) ?></p>
<?php endforeach; ?>
</div>
<?php if ($_SESSION['role'] === 'admin'): ?>
<div class="card flag-card"><p class="flag"><?= htmlspecialchars($flag) ?></p></div>
<?php endif; ?>
<div class="nav">
<a href="transfer.php">Transfer</a> | <a href="search.php">Users</a> | <a href="feedback.php">Feedback</a> | <a href="profile.php">Profile</a> | <a href="ping.php">Ping</a> | <a href="files.php">Files</a> | <a href="admin.php">Admin</a> | <a href="logout.php">Logout</a>
</div>
</div></body></html>"""

TRANSFER_PHP = r"""<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/bank.db');
$msg = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $from = $_POST['from'] ?? '';
    $to = $_POST['to'] ?? '';
    $amt = floatval($_POST['amount'] ?? 0);
    $memo = $_POST['memo'] ?? '';
    $db->exec("UPDATE accounts SET balance = balance - $amt WHERE account_no = '$from'");
    $db->exec("UPDATE accounts SET balance = balance + $amt WHERE account_no = '$to'");
    $db->exec("INSERT INTO transfers (from_acc, to_acc, amount, memo) VALUES ('$from','$to',$amt,'$memo')");
    $msg = "Transfer of \$$amt from $from to $to completed.";
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Transfer</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>Transfer Funds</h1>
<?php if ($msg): ?><p class="success"><?= $msg ?></p><?php endif; ?>
<form method="POST">
<input type="text" name="from" placeholder="From account (ACC-XXXX)" value="ACC-0002">
<input type="text" name="to" placeholder="To account (ACC-XXXX)" value="ACC-0001">
<input type="number" step="0.01" name="amount" placeholder="Amount" value="100">
<input type="text" name="memo" placeholder="Memo (XSS test: <script>alert(1)</script>)">
<button type="submit">Send</button>
</form>
<p class="hint">Try IDOR: send from someone else's account, or SQLi in memo field.</p>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

SEARCH_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/bank.db');
$q = $_GET['q'] ?? '';
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Search Users</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>User Search</h1>
<form method="GET"><input type="text" name="q" placeholder="Search users..." value="<?= htmlspecialchars($q) ?>"><button type="submit">Search</button></form>
<?php if ($q): $results = $db->query("SELECT * FROM users WHERE username LIKE '%$q%' OR full_name LIKE '%$q%'");
if ($results && $results->rowCount()): ?>
<table><tr><th>ID</th><th>Username</th><th>Full Name</th><th>Role</th></tr>
<?php foreach ($results as $r): ?><tr><td><?= $r['id'] ?></td><td><?= htmlspecialchars($r['username']) ?></td><td><?= htmlspecialchars($r['full_name']) ?></td><td><?= $r['role'] ?></td></tr><?php endforeach; ?>
</table>
<?php else: ?><p>No users found.</p><?php endif; endif; ?>
<p class="hint">SQLi: <strong>' UNION SELECT * FROM users --</strong></p>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

FEEDBACK_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/bank.db');
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $msg = $_POST['message'] ?? '';
    $uid = $_SESSION['user_id'];
    $db->exec("INSERT INTO feedback (user_id, message) VALUES ($uid, '$msg')");
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Feedback</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>Feedback Board</h1>
<form method="POST"><textarea name="message" rows="3" placeholder="Leave a comment..."></textarea><button type="submit">Post</button></form>
<p class="hint">XSS: Try <strong>&lt;script&gt;alert('XSS')&lt;/script&gt;</strong> or <strong>&lt;img src=x onerror=alert(1)&gt;</strong></p>
</div>
<div class="card">
<h2>Recent Feedback</h2>
<?php $items = $db->query("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 10");
foreach ($items as $item): ?>
<div class="comment"><strong>User #<?= $item['user_id'] ?></strong> said: <?= $item['message'] ?></div>
<?php endforeach; ?>
</div>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

PROFILE_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/bank.db');
$uid = $_SESSION['user_id'];
$msg = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['avatar'])) {
    $target = '/var/www/html/uploads/' . basename($_FILES['avatar']['name']);
    if (move_uploaded_file($_FILES['avatar']['tmp_name'], $target)) {
        $db->exec("UPDATE users SET avatar='{$_FILES['avatar']['name']}' WHERE id=$uid");
        $msg = "Avatar uploaded.";
    }
}
$user = $db->query("SELECT * FROM users WHERE id=$uid")->fetch(PDO::FETCH_ASSOC);
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Profile</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>Profile</h1>
<p>Username: <?= htmlspecialchars($user['username']) ?></p>
<p>Full name: <?= htmlspecialchars($user['full_name']) ?></p>
<?php if ($user['avatar']): ?><p>Avatar: <img src="uploads/<?= $user['avatar'] ?>" width="100"></p><?php endif; ?>
<h2>Upload Avatar</h2>
<form method="POST" enctype="multipart/form-data"><input type="file" name="avatar"><button type="submit">Upload</button></form>
<p class="hint">Upload a PHP webshell instead of an image to get RCE.</p>
</div>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

PING_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$output = '';
$target = $_POST['target'] ?? '';
if ($target) {
    $output = shell_exec("ping -c 2 $target 2>&1");
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Ping Tool</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>Network Ping</h1>
<form method="POST"><input type="text" name="target" placeholder="IP or hostname" value="<?= htmlspecialchars($target) ?>"><button type="submit">Ping</button></form>
<?php if ($output): ?><pre><?= htmlspecialchars($output) ?></pre><?php endif; ?>
<p class="hint">Command injection: <strong>127.0.0.1; cat /etc/passwd</strong> or <strong>$(id)</strong></p>
</div>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

FILES_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$file = $_GET['file'] ?? '';
$content = '';
if ($file) {
    $path = '/var/www/html/' . $file;
    if (file_exists($path)) {
        $content = file_get_contents($path);
    } else {
        $content = "File not found: $file";
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>File Viewer</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card">
<h1>File Viewer</h1>
<form method="GET"><input type="text" name="file" placeholder="e.g. style.css" value="<?= htmlspecialchars($file) ?>"><button type="submit">View</button></form>
<?php if ($content !== ''): ?><pre><?= htmlspecialchars($content) ?></pre><?php endif; ?>
<p class="hint">LFI: <strong>../../../etc/passwd</strong> or <strong>../../../flag.txt</strong></p>
</div>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

ADMIN_PHP = """<?php
session_start();
if (!isset($_SESSION['user_id'])) { header("Location: index.php"); exit; }
$db = new PDO('sqlite:/tmp/bank.db');
$result = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && !empty($_POST['sql'])) {
    try {
        $res = $db->query($_POST['sql']);
        if ($res) {
            $rows = $res->fetchAll(PDO::FETCH_ASSOC);
            ob_start();
            echo "<table><tr>";
            if ($rows) foreach (array_keys($rows[0]) as $col) echo "<th>" . htmlspecialchars($col) . "</th>";
            echo "</tr>";
            foreach ($rows as $row) {
                echo "<tr>";
                foreach ($row as $val) echo "<td>" . htmlspecialchars($val) . "</td>";
                echo "</tr>";
            }
            echo "</table>";
            $result = ob_get_clean();
        }
    } catch (Exception $e) {
        $result = "<p class='error'>" . htmlspecialchars($e->getMessage()) . "</p>";
    }
}
$flag = file_get_contents('/var/www/html/flag.txt');
?>
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Admin</title><link rel="stylesheet" href="style.css"></head>
<body>
<div class="container">
<div class="card flag-card"><p class="flag"><?= htmlspecialchars($flag) ?></p></div>
<div class="card">
<h1>Admin SQL Console</h1>
<form method="POST"><textarea name="sql" rows="3" placeholder="SELECT * FROM users"><?= htmlspecialchars($_POST['sql'] ?? '') ?></textarea><button type="submit">Execute</button></form>
<?php if ($result): ?><div class="result"><?= $result ?></div><?php endif; ?>
</div>
<a href="dashboard.php">Back</a>
</div></div></body></html>"""

LOGOUT_PHP = """<?php
session_start();
session_destroy();
header("Location: index.php");
?>"""

INDEX_PHP = """<?php
header("Location: login.php");
?>"""

STYLE_CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f5f5;color:#1f1f1f}
.container{max-width:640px;margin:60px auto;padding:0 20px}
.card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
.card h1{font-size:1.5rem;margin-bottom:8px}.card h2{font-size:1rem;font-weight:600;margin-bottom:12px}
.subtitle{color:#5c5c5c;margin-bottom:16px}
input,textarea,select{width:100%;padding:10px 12px;border:1px solid #d0d0d0;border-radius:8px;font-size:0.9rem;margin-bottom:10px;font-family:inherit}
textarea{font-family:monospace}
button{background:#0067c0;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:600;cursor:pointer}
button:hover{background:#005a9e}
.error{color:#c43e1c;margin-bottom:12px;font-size:0.9rem}
.success{color:#107c41;margin-bottom:12px;font-size:0.9rem}
.hint{margin-top:8px;font-size:0.85rem;color:#5c5c5c}
pre{background:#111827;color:#fff;padding:16px;border-radius:8px;overflow-x:auto;font-size:0.85rem;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px}
th,td{border:1px solid #e0e0e0;padding:8px 12px;text-align:left}
th{background:#f7f7f7}
.flag{font-family:monospace;font-size:1.1rem;color:#107c41;background:#ecfdf3;padding:12px;border-radius:8px;text-align:center}
.flag-card{border-color:#86efac;background:#f0fdf4}
.comment{border-bottom:1px solid #eee;padding:10px 0;font-size:0.9rem}
.nav{margin-top:16px;font-size:0.9rem}a{color:#0067c0}
.result{margin-top:12px;overflow-x:auto}
.login-card{max-width:400px;margin:0 auto}
"""

APP_FILES = {
    "login.php": LOGIN_PHP,
    "index.php": INDEX_PHP,
    "dashboard.php": DASHBOARD_PHP,
    "transfer.php": TRANSFER_PHP,
    "search.php": SEARCH_PHP,
    "feedback.php": FEEDBACK_PHP,
    "profile.php": PROFILE_PHP,
    "ping.php": PING_PHP,
    "files.php": FILES_PHP,
    "admin.php": ADMIN_PHP,
    "logout.php": LOGOUT_PHP,
    "style.css": STYLE_CSS,
}


def deploy(network, host_port):
    from .base import deploy_default

    dockerfile = DOCKERFILE.replace("{{FLAG}}", FLAG)
    return deploy_default(
        network=network,
        host_port=host_port,
        flag=FLAG,
        dockerfile=dockerfile,
        files=dict(APP_FILES),
        image_tag="somacloud-service-vulnbank:latest",
        internal_port=80,
    )
