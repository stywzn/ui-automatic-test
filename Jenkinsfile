// Jenkins 声明式流水线（Declarative Pipeline）
// 作用：和 GitHub Actions 等价——拉代码 → 装环境 → 起 SUT → 跑测试 → 出报告。
// 前提：Jenkins 节点上有 python3、pip、node、curl；装 "Allure" 插件后 allure 步骤才可用。

pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps { checkout scm }               // 拉取仓库代码
        }

        stage('Install deps') {
            steps {
                sh 'pip install -r teampilot-lite/requirements.txt'
                sh 'pip install -r ui-tests/requirements.txt'
            }
        }

        stage('Lint') {
            // 质量卡口：lint 不过就直接失败，后面装浏览器/起 SUT 都不用跑了。
            // 规则集锁在仓库根的 ruff.toml 里，升级 ruff 不会凭空冒出新错误。
            steps {
                sh 'python -m ruff check .'
            }
        }

        stage('Install browser') {
            // 单独一个 stage：浏览器内核 ~2GB，只有 lint 过了才值得装。
            steps {
                sh 'python -m playwright install --with-deps chrome'
            }
        }

        stage('Start SUT') {
            steps {
                // 后台起被测系统，轮询 health 等就绪（&& 保证起来了再往下）
                sh '''
                    cd teampilot-lite
                    nohup python -m uvicorn app:app --port 8000 > sut.log 2>&1 &
                    for i in $(seq 1 20); do
                        curl -sf http://localhost:8000/api/health && break || sleep 1
                    done
                '''
            }
        }

        stage('Run UI tests') {
            steps {
                sh 'cd ui-tests && pytest'
            }
        }
    }

    post {
        always {   // 不管成功失败都出报告——报告最有用的就是看失败
            // 需要 Jenkins 装 Allure 插件
            allure includeProperties: false, results: [[path: 'ui-tests/allure-results']]
            // 归档 HTML 报告
            archiveArtifacts artifacts: 'ui-tests/reports/report.html', allowEmptyArchive: true
            // 结束后杀掉 SUT 进程
            sh 'pkill -f "uvicorn app:app" || true'
        }
    }
}
