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

        if (!data.groups) {
            console.error('INIT command missing data.groups');
            return;
        }

        console.log('🏆 Initializing tournament:', data.tournamentName);

        // Update tournament name
        if (data.tournamentName) {
            this.tournamentState.tournamentName = data.tournamentName;
            const titleEl = document.querySelector('.tournament-title');
            if (titleEl) titleEl.textContent = data.tournamentName;
        }

        // Reset state first
        this.handleReset();

        // Initialize quarterfinal groups with player objects
        const quarterfinalGroups = ['A', 'B', 'C', 'D'];
        for (const groupName of quarterfinalGroups) {
            const playerNames = data.groups[groupName];
            if (playerNames && Array.isArray(playerNames) && playerNames.length === 4) {
                // Create player objects with full state
                this.tournamentState.groups[groupName].players = playerNames.map((name, index) => ({
                    name: name,
                    position: index,
                    rawScores: [null, null, null, null], // Scores for rounds 1-4
                    points: 0,
                    totalRawScore: 0
                }));

                // Update DOM with player names
                playerNames.forEach((name, position) => {
                    this.updatePlayerNode(groupName, position, {
                        name: name,
                        score: 0,
                        points: 0,
                        rank: '-'
                    });
                    this.setPlayerState(groupName, position, 'active');
                });
            }
        }

        // Initialize empty semifinal groups (AB, CD)
        this.tournamentState.groups.AB.players = [];
        this.tournamentState.groups.CD.players = [];

        // Initialize empty finals
        this.tournamentState.finals.players = [];

        // Clear any existing path lighting
        this.clearAllPaths();

        // Reset champion display
        this.clearChampionDisplay();

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

        // Validate required fields
        if (!stage || !group || !round || !scores || !Array.isArray(scores)) {
            console.error('SCORE command missing required fields');
            return;
        }

        // Validate round is 1-4
        if (round < 1 || round > 4) {
            console.error('SCORE command: round must be 1-4');
            return;
        }

        console.log(`📝 Score update: ${stage} Group ${group}, Round ${round}`, scores);

        // Get the group state based on stage
        let groupState;
        if (stage === 'final') {
            groupState = this.tournamentState.finals;
        } else if (this.tournamentState.groups[group]) {
            groupState = this.tournamentState.groups[group];
        } else {
            console.error(`Unknown group: ${group}`);
            return;
        }

        // Store the score data
        groupState.scores.push({
            round,
            scores
        });

        // Calculate ranks by sorting scores descending
        const sortedScores = [...scores].sort((a, b) => b.score - a.score);
        const ranks = new Map();
        sortedScores.forEach((s, index) => {
            ranks.set(s.player, index + 1); // 1st, 2nd, 3rd, 4th
        });

        // Update each player's data
        for (const scoreData of scores) {
            const playerName = scoreData.player;
            const rawScore = scoreData.score;
            const rank = ranks.get(playerName);
            const points = this.calculatePoints(rank);

            // Find player in group
            const player = groupState.players.find(p => p && p.name === playerName);
            if (player) {
                // Store raw score for this round (round is 1-indexed, array is 0-indexed)
                player.rawScores[round - 1] = rawScore;

                // Calculate total raw score
                player.totalRawScore = player.rawScores.reduce((sum, s) => sum + (s || 0), 0);

                // Add points for this round
                player.points += points;

                // Update DOM
                this.updatePlayerNode(group, player.position, {
                    score: rawScore,
                    points: player.points,
                    rank: rank
                });
            }
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

        // Validate required fields
        if (!stage || !group) {
            console.error('SETTLE command missing required fields');
            return;
        }

        console.log(`🏁 Settling ${stage} Group ${group}`);

        // Get the group state
        let groupState;
        if (stage === 'final') {
            groupState = this.tournamentState.finals;
        } else if (this.tournamentState.groups[group]) {
            groupState = this.tournamentState.groups[group];
        } else {
            console.error(`Unknown group: ${group}`);
            return;
        }

        groupState.settled = true;

        // Sort players by points (desc), then totalRawScore (desc) for tiebreaker
        const sortedPlayers = [...groupState.players].sort((a, b) => {
            if (b.points !== a.points) {
                return b.points - a.points; // Higher points first
            }
            return b.totalRawScore - a.totalRawScore; // Higher raw score as tiebreaker
        });

        // Top 2 advance, bottom 2 eliminated
        const advancing = sortedPlayers.slice(0, 2);
        const eliminated = sortedPlayers.slice(2);

        // Mark eliminated players
        for (const player of eliminated) {
            this.setPlayerState(group, player.position, 'eliminated');
        }

        // Mark advancing players and light paths
        for (const player of advancing) {
            this.setPlayerState(group, player.position, 'advancing');
        }

        // Store advancing players in group state
        groupState.advancing = advancing.map(p => ({ ...p }));

        // Handle advancement to next stage
        if (stage === 'quarterfinal') {
            // Quarterfinal to semifinal advancement
            let targetGroup;
            let positionOffset = 0;

            if (group === 'A') {
                targetGroup = 'AB';
                positionOffset = 0;
            } else if (group === 'B') {
                targetGroup = 'AB';
                positionOffset = 2;
            } else if (group === 'C') {
                targetGroup = 'CD';
                positionOffset = 0;
            } else if (group === 'D') {
                targetGroup = 'CD';
                positionOffset = 2;
            }

            if (targetGroup) {
                const targetState = this.tournamentState.groups[targetGroup];

                // Light paths from quarterfinal to semifinal
                for (let i = 0; i < advancing.length; i++) {
                    const player = advancing[i];
                    const targetPosition = positionOffset + i;
                    const fromId = `${group}-${player.position}`;
                    const toId = `${targetGroup}-${targetPosition}`;

                    this.lightPath(fromId, toId);

                    // Copy player data to next stage
                    const advancedPlayer = {
                        name: player.name,
                        position: targetPosition,
                        rawScores: [null, null, null, null],
                        points: 0,
                        totalRawScore: 0
                    };

                    // Add to target group players array
                    if (!targetState.players[targetPosition]) {
                        targetState.players[targetPosition] = advancedPlayer;
                    }

                    // Update DOM for next stage node
                    this.updatePlayerNode(targetGroup, targetPosition, {
                        name: player.name,
                        score: 0,
                        points: 0,
                        rank: '-'
                    });
                    this.setPlayerState(targetGroup, targetPosition, 'active');
                }
            }
        } else if (stage === 'semifinal') {
            // Semifinal to final advancement
            let positionOffset = 0;

            if (group === 'AB') {
                positionOffset = 0;
            } else if (group === 'CD') {
                positionOffset = 2;
            }

            const finalsState = this.tournamentState.finals;

            // Light paths from semifinal to final
            for (let i = 0; i < advancing.length; i++) {
                const player = advancing[i];
                const targetPosition = positionOffset + i;
                const fromId = `${group}-${player.position}`;
                const toId = `finals-${targetPosition}`;

                this.lightPath(fromId, toId);

                // Copy player data to finals
                const advancedPlayer = {
                    name: player.name,
                    position: targetPosition,
                    rawScores: [null, null, null, null],
                    points: 0,
                    totalRawScore: 0
                };

                // Add to finals players array
                if (!finalsState.players[targetPosition]) {
                    finalsState.players[targetPosition] = advancedPlayer;
                }

                // Update DOM for finals node
                this.updatePlayerNode('finals', targetPosition, {
                    name: player.name,
                    score: 0,
                    points: 0,
                    rank: '-'
                });
                this.setPlayerState('finals', targetPosition, 'active');
            }
        } else if (stage === 'final') {
            // Determine champion
            const champion = sortedPlayers[0];
            if (champion) {
                this.tournamentState.finals.champion = champion;

                // Update champion display
                const championEl = document.querySelector('.champion-name');
                if (championEl) {
                    championEl.textContent = champion.name;
                }

                // Light champion path
                this.lightChampionPath(champion);
            }
        }
    }

    /**
     * Reset tournament to initial state
     */
    handleReset() {
        console.log('🔄 Resetting tournament');

        // Reset tournament state
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

        // Clear all player nodes (reset to 'TBD', 0, '-')
        const allGroups = ['A', 'B', 'C', 'D', 'AB', 'CD'];
        for (const group of allGroups) {
            for (let position = 0; position < 4; position++) {
                this.updatePlayerNode(group, position, {
                    name: 'TBD',
                    score: 0,
                    points: 0,
                    rank: '-'
                });
                this.setPlayerState(group, position, '');
            }
        }

        // Clear finals nodes
        for (let position = 0; position < 4; position++) {
            this.updatePlayerNode('finals', position, {
                name: 'TBD',
                score: 0,
                points: 0,
                rank: '-'
            });
            this.setPlayerState('finals', position, '');
        }

        // Clear all path lighting
        this.clearAllPaths();

        // Clear champion display
        this.clearChampionDisplay();

        // Reset tournament name
        const titleEl = document.querySelector('.tournament-title');
        if (titleEl) titleEl.textContent = '淘汰赛';
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
        // No-op: user doesn't want connection lines
        return;
    }

    // ==========================================
    // Tournament Helper Methods
    // ==========================================

    /**
     * Calculate points based on rank
     * @param {number} rank - Player rank (1st, 2nd, 3rd, 4th)
     * @returns {number} Points awarded (2, 1, or 0)
     */
    calculatePoints(rank) {
        switch (rank) {
            case 1: return 2; // 1st place: 2 points
            case 2: return 1; // 2nd place: 1 point
            case 3:
            case 4: return 0; // 3rd/4th place: 0 points
            default: return 0;
        }
    }

    /**
     * Clear all path lighting
     */
    clearAllPaths() {
        // No-op: user doesn't want connection lines
        return;
    }

    /**
     * Clear champion display
     */
    clearChampionDisplay() {
        const championEl = document.querySelector('.champion-name');
        if (championEl) {
            championEl.textContent = '???';
        }
    }

    /**
     * Light up the full champion progression path
     * @param {Object} champion - Champion player object
     */
    lightChampionPath(champion) {
        // Find which quarterfinal group the champion came from
        let quarterfinalGroup = null;
        let quarterfinalPosition = null;
        let semifinalGroup = null;
        let semifinalPosition = null;
        let finalPosition = null;

        // Search through finals to find champion position
        for (let i = 0; i < this.tournamentState.finals.players.length; i++) {
            const player = this.tournamentState.finals.players[i];
            if (player && player.name === champion.name) {
                finalPosition = i;
                break;
            }
        }

        if (finalPosition === null) return;

        // Determine which semifinal group the champion came from
        if (finalPosition < 2) {
            semifinalGroup = 'AB';
            semifinalPosition = finalPosition;
        } else {
            semifinalGroup = 'CD';
            semifinalPosition = finalPosition - 2;
        }

        // Find champion in semifinal group
        const semifinalPlayers = this.tournamentState.groups[semifinalGroup].players;
        for (let i = 0; i < semifinalPlayers.length; i++) {
            const player = semifinalPlayers[i];
            if (player && player.name === champion.name) {
                // Light path from semifinal to final
                this.lightPath(`${semifinalGroup}-${i}`, `finals-${finalPosition}`, true);

                // Determine which quarterfinal group the champion came from
                if (semifinalGroup === 'AB') {
                    if (i < 2) {
                        quarterfinalGroup = 'A';
                        quarterfinalPosition = i;
                    } else {
                        quarterfinalGroup = 'B';
                        quarterfinalPosition = i - 2;
                    }
                } else {
                    if (i < 2) {
                        quarterfinalGroup = 'C';
                        quarterfinalPosition = i;
                    } else {
                        quarterfinalGroup = 'D';
                        quarterfinalPosition = i - 2;
                    }
                }

                // Light path from quarterfinal to semifinal
                if (quarterfinalGroup !== null) {
                    this.lightPath(`${quarterfinalGroup}-${quarterfinalPosition}`, `${semifinalGroup}-${i}`, true);
                }
                break;
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tournament = new TournamentApp();
});
