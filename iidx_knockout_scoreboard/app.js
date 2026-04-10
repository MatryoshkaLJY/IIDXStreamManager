/**
 * Knockout Tournament Scoreboard - Main Application
 *
 * WebSocket Command Protocol:
 *
 * 1. INIT - Initialize tournament
 * {
 *   "cmd": "init",
 *   "data": {
 *     "tournamentName": "16人淘汰赛",
 *     "groups": {
 *       "A": ["Player1", "Player2", "Player3", "Player4"],
 *       "B": ["Player5", "Player6", "Player7", "Player8"],
 *       "C": ["Player9", "Player10", "Player11", "Player12"],
 *       "D": ["Player13", "Player14", "Player15", "Player16"]
 *     }
 *   }
 * }
 *
 * 2. SCORE - Record song scores
 * {
 *   "cmd": "score",
 *   "data": {
 *     "stage": "quarterfinal",
 *     "group": "A",
 *     "round": 1,
 *     "scores": [
 *       {"player": "Player1", "score": 980000},
 *       {"player": "Player2", "score": 950000},
 *       {"player": "Player3", "score": 920000},
 *       {"player": "Player4", "score": 890000}
 *     ]
 *   }
 * }
 *
 * 3. SETTLE - Finalize round
 * {
 *   "cmd": "settle",
 *   "data": {
 *     "stage": "quarterfinal",
 *     "group": "A"
 *   }
 * }
 *
 * 4. RESET - Clear tournament
 * {
 *   "cmd": "reset"
 * }
 */

class TournamentApp {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 3000;
        this.wsUrl = 'ws://localhost:8081';

        // Tournament state
        this.tournamentState = {
            tournamentName: '',
            groups: {
                A: { players: [], scores: [], settled: false, advancing: [] },
                B: { players: [], scores: [], settled: false, advancing: [] },
                C: { players: [], scores: [], settled: false, advancing: [] },
                D: { players: [], scores: [], settled: false, advancing: [] },
                AB: { players: [], scores: [], settled: false, advancing: [] },
                CD: { players: [], scores: [], settled: false, advancing: [] }
            },
            finals: { players: [], scores: [], settled: false, champion: null },
            currentStage: 'quarterfinal'
        };

        // DOM element cache
        this.els = {
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text')
        };

        this.init();
    }

    init() {
        this.connectWebSocket();
        console.log('🏆 Knockout Tournament Scoreboard initialized');
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
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleCommand(message);
                } catch (error) {
                    console.error('❌ Invalid message format:', error);
                }
            };

            this.ws.onclose = () => {
                console.log('🔴 WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
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
        if (this.els.statusDot) {
            this.els.statusDot.className = 'status-dot ' + status;
        }

        if (this.els.statusText) {
            const statusTexts = {
                connected: '已连接',
                connecting: '连接中...',
                disconnected: '离线',
                error: '连接错误'
            };
            this.els.statusText.textContent = statusTexts[status] || '未知';
        }
    }

    // ==========================================
    // Command Handlers
    // ==========================================

    handleCommand(message) {
        if (!message.cmd) {
            console.error('Missing cmd field:', message);
            return;
        }

        console.log(`📨 Received command: ${message.cmd}`);

        switch (message.cmd) {
            case 'init':
                this.handleInit(message.data);
                break;
            case 'score':
                this.handleScore(message.data);
                break;
            case 'settle':
                this.handleSettle(message.data);
                break;
            case 'reset':
                this.handleReset();
                break;
            default:
                console.warn('Unknown command:', message.cmd);
        }
    }

    /**
     * Initialize tournament with player groups
     */
    handleInit(data) {
        if (!data) {
            console.error('INIT command missing data');
            return;
        }

        console.log('🏆 Initializing tournament:', data.tournamentName);

        // Update tournament name
        if (data.tournamentName) {
            this.tournamentState.tournamentName = data.tournamentName;
        }

        // Initialize groups
        if (data.groups) {
            for (const [groupName, players] of Object.entries(data.groups)) {
                if (this.tournamentState.groups[groupName]) {
                    this.tournamentState.groups[groupName].players = players;
                    this.tournamentState.groups[groupName].scores = [];
                    this.tournamentState.groups[groupName].settled = false;
                    this.tournamentState.groups[groupName].advancing = [];
                }
            }
        }

        this.tournamentState.currentStage = 'quarterfinal';
        console.log('Tournament initialized:', this.tournamentState);
    }

    /**
     * Record scores for a song in a round
     */
    handleScore(data) {
        if (!data) {
            console.error('SCORE command missing data');
            return;
        }

        const { stage, group, round, scores } = data;
        console.log(`📝 Score update: ${stage} Group ${group}, Round ${round}`, scores);

        // Store the score data
        if (group && this.tournamentState.groups[group]) {
            this.tournamentState.groups[group].scores.push({
                round,
                scores
            });
        } else if (stage === 'final') {
            this.tournamentState.finals.scores.push({
                round,
                scores
            });
        }
    }

    /**
     * Finalize a round and determine advancing players
     */
    handleSettle(data) {
        if (!data) {
            console.error('SETTLE command missing data');
            return;
        }

        const { stage, group } = data;
        console.log(`🏁 Settling ${stage} Group ${group}`);

        if (group && this.tournamentState.groups[group]) {
            this.tournamentState.groups[group].settled = true;
            // Calculate advancing players (top 2 by points)
            // This will be implemented in the next phase
        } else if (stage === 'final') {
            this.tournamentState.finals.settled = true;
            // Determine champion
        }
    }

    /**
     * Reset tournament to initial state
     */
    handleReset() {
        console.log('🔄 Resetting tournament');

        this.tournamentState = {
            tournamentName: '',
            groups: {
                A: { players: [], scores: [], settled: false, advancing: [] },
                B: { players: [], scores: [], settled: false, advancing: [] },
                C: { players: [], scores: [], settled: false, advancing: [] },
                D: { players: [], scores: [], settled: false, advancing: [] },
                AB: { players: [], scores: [], settled: false, advancing: [] },
                CD: { players: [], scores: [], settled: false, advancing: [] }
            },
            finals: { players: [], scores: [], settled: false, champion: null },
            currentStage: 'quarterfinal'
        };
    }

    // ==========================================
    // DOM Helper Methods
    // ==========================================

    /**
     * Get player node element by group and position
     * @param {string} group - Group name (A, B, C, D, AB, CD, finals)
     * @param {number} position - Player position (0-3)
     * @returns {Element|null} Player node element
     */
    getPlayerNode(group, position) {
        return document.querySelector(`[data-group="${group}"][data-position="${position}"]`);
    }

    /**
     * Get SVG path element connecting two nodes
     * @param {string} from - Source node identifier (e.g., "A-0")
     * @param {string} to - Target node identifier (e.g., "AB-0")
     * @returns {Element|null} SVG path element
     */
    getPath(from, to) {
        return document.querySelector(`[data-path="${from}-${to}"]`);
    }

    /**
     * Update player node with data
     * @param {string} group - Group name
     * @param {number} position - Player position
     * @param {Object} data - Player data {name, score, points, rank}
     */
    updatePlayerNode(group, position, data) {
        const node = this.getPlayerNode(group, position);
        if (!node) return;

        if (data.name !== undefined) {
            const nameEl = node.querySelector('.player-name');
            if (nameEl) nameEl.textContent = data.name;
        }

        if (data.score !== undefined) {
            const scoreEl = node.querySelector('.player-score');
            if (scoreEl) scoreEl.textContent = data.score.toLocaleString();
        }

        if (data.points !== undefined) {
            const pointsEl = node.querySelector('.player-points');
            if (pointsEl) pointsEl.textContent = `${data.points} pts`;
        }

        if (data.rank !== undefined) {
            const rankEl = node.querySelector('.player-rank');
            if (rankEl) {
                rankEl.textContent = data.rank;
                rankEl.className = 'player-rank rank-' + data.rank;
            }
        }
    }

    /**
     * Set player node state (active, eliminated, advancing)
     * @param {string} group - Group name
     * @param {number} position - Player position
     * @param {string} state - State: 'active', 'eliminated', 'advancing'
     */
    setPlayerState(group, position, state) {
        const node = this.getPlayerNode(group, position);
        if (!node) return;

        // Remove existing state classes
        node.classList.remove('active', 'eliminated', 'advancing');

        // Add new state class
        if (state) {
            node.classList.add(state);
        }
    }

    /**
     * Light up a path between nodes
     * @param {string} from - Source node identifier
     * @param {string} to - Target node identifier
     * @param {boolean} isChampion - Whether this is the champion path
     */
    lightPath(from, to, isChampion = false) {
        const path = this.getPath(from, to);
        if (!path) return;

        path.classList.add('lit');
        if (isChampion) {
            path.classList.add('champion-path');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tournament = new TournamentApp();
});
