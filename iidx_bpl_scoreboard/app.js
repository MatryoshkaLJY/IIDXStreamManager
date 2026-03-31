/**
 * BPL Scoreboard - Main Application
 *
 * WebSocket Command Protocol:
 *
 * 1. INIT - Initialize match
 * {
 *   "cmd": "init",
 *   "data": {
 *     "stageName": "レギュラーステージ",
 *     "matchNumber": 1,
 *     "leftTeam": {
 *       "name": "SILK HAT",
 *       "logo": "🎩",
 *       "colors": { "primary": "#c0c0c0", "secondary": "#ffffff" }
 *     },
 *     "rightTeam": { ... },
 *     "matches": [
 *       {
 *         "type": "1v1",           // or "2v2"
 *         "leftPlayers": ["CHEPY."],
 *         "rightPlayers": ["TAKA.S"],
 *         "theme": "NOTES"
 *       },
 *       {
 *         "type": "2v2",
 *         "leftPlayers": ["PLAYER1", "PLAYER2"],
 *         "rightPlayers": ["PLAYER3", "PLAYER4"],
 *         "theme": "SCRATCH"
 *       }
 *     ]
 *   }
 * }
 *
 * 2. SCORE - Update scores
 * {
 *   "cmd": "score",
 *   "data": {
 *     "round": 1,              // 1-based round number
 *     "leftScore": 2,
 *     "rightScore": 0
 *   }
 * }
 *
 * 3. RESET - Reset all scores
 * {
 *   "cmd": "reset"
 * }
 */

class ScoreboardApp {
    constructor() {
        this.config = null;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.wsUrl = 'ws://localhost:8080';
        this.matchData = []; // Store match configurations
        this.scores = [];    // Store current scores
        this.revealedMatches = new Set(); // Tracks which matches have revealed players

        // DOM elements
        this.els = {
            stageName: document.querySelector('.stage-name'),
            matchNumber: document.querySelector('.match-number .number'),
            leftTeam: {
                logo: document.querySelector('.left-team .team-logo'),
                name: document.querySelector('.left-team .team-name'),
                score: document.querySelector('.left-team .score-value')
            },
            rightTeam: {
                logo: document.querySelector('.right-team .team-logo'),
                name: document.querySelector('.right-team .team-name'),
                score: document.querySelector('.right-team .score-value')
            },
            matchDetails: document.getElementById('matchDetails'),
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            messageLog: document.getElementById('messageLog')
        };

        this.init();
    }

    init() {
        this.connectWebSocket();
        console.log('🎮 BPL Scoreboard initialized');

        // Debug: Show debug panel with '?debug=1' in URL
        if (window.location.search.includes('debug=1')) {
            document.getElementById('debugPanel').style.display = 'block';
        }
    }

    // ==========================================
    // WebSocket Connection
    // ==========================================

    connectWebSocket() {
        this.updateConnectionStatus('connecting');

        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => {
                console.log('🟢 WebSocket connected');
                this.updateConnectionStatus('connected');
                this.logMessage('Connected to WebSocket server', 'system');
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleCommand(message);
                } catch (error) {
                    console.error('❌ Invalid message format:', error);
                    this.logMessage('Invalid message format: ' + event.data, 'error');
                }
            };

            this.ws.onclose = () => {
                console.log('🔴 WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                this.logMessage('Disconnected, retrying...', 'error');
                setTimeout(() => this.connectWebSocket(), this.reconnectInterval);
            };

            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.updateConnectionStatus('error');
            };
        } catch (error) {
            console.error('❌ Failed to connect:', error);
            this.updateConnectionStatus('error');
            setTimeout(() => this.connectWebSocket(), this.reconnectInterval);
        }
    }

    updateConnectionStatus(status) {
        this.els.statusDot.className = 'status-dot ' + status;

        const statusTexts = {
            connected: '已连接',
            connecting: '连接中...',
            disconnected: '离线',
            error: '连接错误'
        };
        this.els.statusText.textContent = statusTexts[status] || '未知';
    }

    // ==========================================
    // Command Handlers
    // ==========================================

    handleCommand(message) {
        if (!message.cmd) {
            console.error('Missing cmd field:', message);
            return;
        }

        this.logMessage(`Received: ${message.cmd}`, message.cmd);

        switch (message.cmd) {
            case 'init':
                this.handleInit(message.data);
                break;
            case 'score':
                this.handleScore(message.data);
                break;
            case 'reset':
                this.handleReset();
                break;
            default:
                console.warn('Unknown command:', message.cmd);
        }
    }

    /**
     * Initialize match with team info and player assignments
     */
    handleInit(data) {
        if (!data) {
            console.error('INIT command missing data');
            return;
        }

        console.log('🎮 Initializing match:', data);

        // Update stage info
        if (data.stageName) {
            this.els.stageName.textContent = data.stageName;
        }
        if (data.matchNumber !== undefined) {
            this.els.matchNumber.textContent = data.matchNumber;
        }

        // Update left team
        if (data.leftTeam) {
            const team = data.leftTeam;
            this.els.leftTeam.logo.textContent = team.logo || '🎩';
            this.els.leftTeam.name.textContent = team.name || 'LEFT TEAM';
            this.els.leftTeam.score.textContent = '0';

            if (team.colors) {
                this.applyTeamColors('left', team.colors);
            }
        }

        // Update right team
        if (data.rightTeam) {
            const team = data.rightTeam;
            this.els.rightTeam.logo.textContent = team.logo || '🎮';
            this.els.rightTeam.name.textContent = team.name || 'RIGHT TEAM';
            this.els.rightTeam.score.textContent = '0';

            if (team.colors) {
                this.applyTeamColors('right', team.colors);
            }
        }

        // Store match configuration
        this.matchData = data.matches || [];
        this.revealedMatches.clear();

        // Initialize scores
        this.scores = this.matchData.map(() => ({ left: null, right: null }));

        // Render match rows
        this.renderMatchRows();

        this.logMessage(`Match initialized: ${this.matchData.length} rounds`, 'init');
    }

    /**
     * Update score for a specific round
     */
    handleScore(data) {
        if (!data || data.round === undefined) {
            console.error('SCORE command missing round');
            return;
        }

        const roundIndex = data.round - 1; // Convert to 0-based
        if (roundIndex < 0 || roundIndex >= this.matchData.length) {
            console.error('Invalid round number:', data.round);
            return;
        }

        // Update score
        this.scores[roundIndex] = {
            left: data.leftScore ?? null,
            right: data.rightScore ?? null
        };

        // Reveal players for this round
        this.revealedMatches.add(roundIndex);

        // Update UI
        this.updateRoundScore(roundIndex);
        this.updateTotalScores();
        this.revealPlayers(roundIndex);

        this.logMessage(
            `Round ${data.round}: ${data.leftScore} - ${data.rightScore}`,
            'score'
        );
    }

    /**
     * Reset all scores
     */
    handleReset() {
        this.scores = this.matchData.map(() => ({ left: null, right: null }));
        this.revealedMatches.clear();

        // Reset UI
        this.els.leftTeam.score.textContent = '0';
        this.els.rightTeam.score.textContent = '0';

        this.matchData.forEach((_, index) => {
            this.updateRoundScore(index);
            this.hidePlayers(index);
        });

        this.logMessage('Scores reset', 'system');
    }

    // ==========================================
    // UI Rendering
    // ==========================================

    applyTeamColors(side, colors) {
        const root = document.documentElement;
        const prefix = side === 'left' ? '--left' : '--right';

        if (colors.primary) {
            root.style.setProperty(`${prefix}-primary`, colors.primary);

            // Generate gradient colors from primary color
            const gradientColors = this.generateGradientColors(colors.primary);
            root.style.setProperty(`${prefix}-bg-start`, gradientColors.start);
            root.style.setProperty(`${prefix}-bg-end`, gradientColors.end);
        }
        if (colors.secondary) {
            root.style.setProperty(`${prefix}-secondary`, colors.secondary);
        }
        if (colors.accent) {
            root.style.setProperty(`${prefix}-accent`, colors.accent);
        }
    }

    /**
     * Generate gradient colors from a base color
     * Darkens the base color for start, lightens for end
     */
    generateGradientColors(baseColor) {
        // Parse hex color
        let hex = baseColor.replace('#', '');
        if (hex.length === 3) {
            hex = hex.split('').map(c => c + c).join('');
        }

        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);

        // Darken for start (multiply by 0.3)
        const darken = (c) => Math.max(0, Math.floor(c * 0.3));
        // Lighten for end (blend with white)
        const lighten = (c) => Math.min(255, Math.floor(c * 0.8 + 64));

        const startColor = `#${darken(r).toString(16).padStart(2, '0')}${darken(g).toString(16).padStart(2, '0')}${darken(b).toString(16).padStart(2, '0')}`;
        const endColor = `#${lighten(r).toString(16).padStart(2, '0')}${lighten(g).toString(16).padStart(2, '0')}${lighten(b).toString(16).padStart(2, '0')}`;

        return { start: startColor, end: endColor };
    }

    renderMatchRows() {
        this.els.matchDetails.innerHTML = '';

        this.matchData.forEach((match, index) => {
            const row = document.createElement('div');
            row.className = 'match-row';
            row.dataset.match = index;

            const isRevealed = this.revealedMatches.has(index);
            const score = this.scores[index] || { left: null, right: null };

            // Match number label
            const matchNum = index + 1;
            const suffix = ['st', 'nd', 'rd', 'th'][Math.min(matchNum - 1, 3)];

            row.innerHTML = `
                <div class="player-section left ${isRevealed ? 'revealed' : 'hidden'}">
                    ${this.renderPlayerNames(match.leftPlayers, match.type)}
                </div>
                <div class="match-score left-score ${score.left === null ? 'hidden' : ''}">
                    ${score.left !== null ? score.left : '-'}
                </div>
                <div class="match-info">
                    <span class="match-label">${matchNum}${suffix} MATCH</span>
                    <span class="match-theme" data-theme="${match.theme || ''}">${match.theme || ''}</span>
                </div>
                <div class="match-score right-score ${score.right === null ? 'hidden' : ''}">
                    ${score.right !== null ? score.right : '-'}
                </div>
                <div class="player-section right ${isRevealed ? 'revealed' : 'hidden'}">
                    ${this.renderPlayerNames(match.rightPlayers, match.type)}
                </div>
            `;

            this.els.matchDetails.appendChild(row);
        });
    }

    renderPlayerNames(players, type) {
        if (!players || players.length === 0) {
            return '<span class="player-name">TBD</span>';
        }

        if (type === '2v2' && players.length === 2) {
            return `
                <span class="player-name">${players[0]}</span>
                <span class="player-name">${players[1]}</span>
            `;
        }

        return `<span class="player-name">${players[0]}</span>`;
    }

    updateRoundScore(roundIndex) {
        const row = this.els.matchDetails.querySelector(`[data-match="${roundIndex}"]`);
        if (!row) return;

        const score = this.scores[roundIndex];
        const leftScoreEl = row.querySelector('.left-score');
        const rightScoreEl = row.querySelector('.right-score');

        // Update left score
        if (score.left !== null) {
            if (leftScoreEl.textContent.trim() !== String(score.left)) {
                leftScoreEl.textContent = score.left;
                leftScoreEl.classList.remove('hidden');
                leftScoreEl.classList.add('score-updating');
                setTimeout(() => leftScoreEl.classList.remove('score-updating'), 500);
            }
        } else {
            leftScoreEl.textContent = '-';
            leftScoreEl.classList.add('hidden');
        }

        // Update right score
        if (score.right !== null) {
            if (rightScoreEl.textContent.trim() !== String(score.right)) {
                rightScoreEl.textContent = score.right;
                rightScoreEl.classList.remove('hidden');
                rightScoreEl.classList.add('score-updating');
                setTimeout(() => rightScoreEl.classList.remove('score-updating'), 500);
            }
        } else {
            rightScoreEl.textContent = '-';
            rightScoreEl.classList.add('hidden');
        }
    }

    updateTotalScores() {
        let leftTotal = 0;
        let rightTotal = 0;

        this.scores.forEach(score => {
            if (score.left !== null) leftTotal += score.left;
            if (score.right !== null) rightTotal += score.right;
        });

        this.animateScoreUpdate(this.els.leftTeam.score, leftTotal);
        this.animateScoreUpdate(this.els.rightTeam.score, rightTotal);
    }

    animateScoreUpdate(element, newValue) {
        const currentValue = parseInt(element.textContent) || 0;
        if (currentValue !== newValue) {
            element.textContent = newValue;
            element.classList.add('updating');
            setTimeout(() => element.classList.remove('updating'), 400);
        }
    }

    revealPlayers(roundIndex) {
        const row = this.els.matchDetails.querySelector(`[data-match="${roundIndex}"]`);
        if (!row) return;

        const leftSection = row.querySelector('.player-section.left');
        const rightSection = row.querySelector('.player-section.right');

        leftSection.classList.remove('hidden');
        leftSection.classList.add('revealed');
        rightSection.classList.remove('hidden');
        rightSection.classList.add('revealed');
    }

    hidePlayers(roundIndex) {
        const row = this.els.matchDetails.querySelector(`[data-match="${roundIndex}"]`);
        if (!row) return;

        const leftSection = row.querySelector('.player-section.left');
        const rightSection = row.querySelector('.player-section.right');

        leftSection.classList.remove('revealed');
        leftSection.classList.add('hidden');
        rightSection.classList.remove('revealed');
        rightSection.classList.add('hidden');
    }

    // ==========================================
    // Debug Logging
    // ==========================================

    logMessage(message, type) {
        console.log(`[${type}] ${message}`);

        if (!this.els.messageLog) return;

        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;

        this.els.messageLog.appendChild(entry);
        this.els.messageLog.scrollTop = this.els.messageLog.scrollHeight;

        // Keep only last 50 messages
        while (this.els.messageLog.children.length > 50) {
            this.els.messageLog.removeChild(this.els.messageLog.firstChild);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.scoreboard = new ScoreboardApp();
});
