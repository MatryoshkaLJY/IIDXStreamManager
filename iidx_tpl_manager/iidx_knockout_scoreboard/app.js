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
                E: { players: [], scores: [], settled: false, advancing: [] },
                F: { players: [], scores: [], settled: false, advancing: [] }
            },
            finals: { players: [], scores: [], settled: false, inTiebreaker: false },
            currentStage: 'quarterfinal',
            currentActiveGroup: null
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
            case 'continue':
                this.handleContinue();
                break;
            case 'reset':
                this.handleReset();
                break;
            default:
                console.warn('Unknown command:', message.cmd);
        }
    }

    /**
     * Continue to the next stage after current group is settled.
     * Removes active highlight from current group and activates the next one.
     */
    handleContinue() {
        const currentGroup = this.tournamentState.currentActiveGroup;
        if (!currentGroup) {
            console.log('No active group to continue from');
            return;
        }

        console.log(`➡️ Continue from Group ${currentGroup}`);

        const groupOrder = ['A', 'B', 'C', 'D', 'E', 'F', 'finals'];
        const currentIndex = groupOrder.indexOf(currentGroup);
        if (currentIndex !== -1 && currentIndex < groupOrder.length - 1) {
            const nextGroup = groupOrder[currentIndex + 1];
            this.tournamentState.currentActiveGroup = nextGroup;
            this.highlightGroup(nextGroup);
            this.updateStageIndicator(nextGroup);
        } else {
            console.log('Already at the final stage');
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

        // Reset state first
        this.handleReset();

        // Update tournament name
        if (data.tournamentName) {
            this.tournamentState.tournamentName = data.tournamentName;
            const titleEl = document.querySelector('.tournament-title');
            if (titleEl) {
                const titleTextEl = titleEl.querySelector('.title-text');
                if (titleTextEl) titleTextEl.textContent = data.tournamentName;
            }
        }

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
                });
            }
        }

        // Initialize empty semifinal groups (E, F)
        this.tournamentState.groups.E.players = [];
        this.tournamentState.groups.F.players = [];

        // Initialize empty finals
        this.tournamentState.finals.players = [];
        this.tournamentState.finals.inTiebreaker = false;

        // Clear any existing path lighting
        this.clearAllPaths();

        this.tournamentState.currentStage = 'quarterfinal';
        this.tournamentState.currentActiveGroup = 'A';
        this.highlightGroup('A');
        this.updateStageIndicator('A');
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

                let displayScore;
                if (stage === 'final') {
                    const finalsState = this.tournamentState.finals;
                    if (finalsState.inTiebreaker) {
                        // Tiebreaker: accumulate tiebreaker score, no points awarded
                        player.tiebreakerScore = (player.tiebreakerScore || 0) + rawScore;
                        displayScore = player.tiebreakerScore;
                    } else {
                        // Finals normal round: display current round score only, do not accumulate totalRawScore
                        player.totalRawScore = 0;
                        displayScore = rawScore;
                        // Add points for this round
                        player.points += points;
                    }
                } else {
                    // A-F groups: accumulate total raw score
                    player.totalRawScore = player.rawScores.reduce((sum, s) => sum + (s || 0), 0);
                    // Add points for this round
                    player.points += points;
                    displayScore = player.totalRawScore;
                }

                // Update DOM
                this.updatePlayerNode(group, player.position, {
                    score: displayScore,
                    points: player.points,
                    rank: rank
                });
            }
        }

        // Auto-settle after 4 rounds for non-final groups
        if (stage !== 'final' && groupState.scores.length === 4 && !groupState.settled) {
            this.handleSettle({ stage, group });
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

        // Sort players based on stage rules
        let sortedPlayers;
        if (stage === 'final') {
            if (groupState.inTiebreaker) {
                sortedPlayers = [...groupState.players].sort((a, b) => {
                    return (b.tiebreakerScore || 0) - (a.tiebreakerScore || 0);
                });
            } else {
                sortedPlayers = [...groupState.players].sort((a, b) => {
                    return b.points - a.points;
                });
            }
        } else {
            // A-F groups: sort by PT then totalRawScore
            sortedPlayers = [...groupState.players].sort((a, b) => {
                if (b.points !== a.points) {
                    return b.points - a.points; // Higher points first
                }
                return b.totalRawScore - a.totalRawScore; // Higher raw score as tiebreaker
            });
        }

        if (stage !== 'final') {
            // Top 2 advance, bottom 2 eliminated
            const advancing = sortedPlayers.slice(0, 2);
            const eliminated = sortedPlayers.slice(2);

            // Mark eliminated players
            for (const player of eliminated) {
                this.setPlayerState(group, player.position, 'eliminated');
            }

            // Mark advancing players (keep strong green glow until continue)
            for (const player of advancing) {
                this.setPlayerState(group, player.position, 'advancing');
                const node = this.getPlayerNode(group, player.position);
                if (node) node.classList.add('active');
            }

            // Store advancing players in group state
            groupState.advancing = advancing.map(p => ({ ...p }));

            // Handle advancement to next stage
            if (stage === 'quarterfinal') {
                const first = sortedPlayers[0];
                const second = sortedPlayers[1];

                if (group === 'A') {
                    this.advancePlayerToGroup(first, group, 'E', 0);
                    this.advancePlayerToGroup(second, group, 'F', 0);
                } else if (group === 'B') {
                    this.advancePlayerToGroup(second, group, 'E', 1);
                    this.advancePlayerToGroup(first, group, 'F', 1);
                } else if (group === 'C') {
                    this.advancePlayerToGroup(second, group, 'E', 2);
                    this.advancePlayerToGroup(first, group, 'F', 2);
                } else if (group === 'D') {
                    this.advancePlayerToGroup(first, group, 'E', 3);
                    this.advancePlayerToGroup(second, group, 'F', 3);
                }
            } else if (stage === 'semifinal') {
                let positionOffset = 0;
                if (group === 'E') {
                    positionOffset = 0;
                } else if (group === 'F') {
                    positionOffset = 2;
                }

                const finalsState = this.tournamentState.finals;
                for (let i = 0; i < advancing.length; i++) {
                    const player = advancing[i];
                    const targetPosition = positionOffset + i;

                    this.lightPath(`${group}-${player.position}`, `finals-${targetPosition}`);

                    const advancedPlayer = {
                        name: player.name,
                        position: targetPosition,
                        rawScores: [null, null, null, null],
                        points: 0,
                        totalRawScore: 0,
                        tiebreakerScore: 0
                    };

                    if (!finalsState.players[targetPosition]) {
                        finalsState.players[targetPosition] = advancedPlayer;
                    }

                    this.updatePlayerNode('finals', targetPosition, {
                        name: player.name,
                        score: 0,
                        points: 0,
                        rank: '-'
                    });
                }
            }
        } else {
            // stage === 'final'
            const medals = ['🥇', '🥈', '🥉', ''];

            if (!groupState.inTiebreaker) {
                // Check for PT ties and group them
                const tieGroups = [];
                let i = 0;
                let hasTie = false;

                while (i < sortedPlayers.length) {
                    let j = i + 1;
                    while (j < sortedPlayers.length && sortedPlayers[j].points === sortedPlayers[i].points) {
                        j++;
                    }
                    const group = sortedPlayers.slice(i, j);
                    if (group.length > 1) {
                        hasTie = true;
                        tieGroups.push({ startRank: i, players: group.map(p => p.position) });
                        // Tie players stay active for tiebreaker
                        for (const p of group) {
                            this.setPlayerState('finals', p.position, 'active');
                        }
                    } else {
                        // No tie - assign medal immediately
                        const player = group[0];
                        const node = this.getPlayerNode('finals', player.position);
                        if (node) {
                            node.classList.remove('active', 'eliminated', 'advancing', 'champion', 'second', 'third');
                            if (i === 0) node.classList.add('champion');
                            else if (i === 1) node.classList.add('second');
                            else if (i === 2) node.classList.add('third');
                            const pointsEl = node.querySelector('.player-points');
                            if (pointsEl) pointsEl.textContent = medals[i] || '';
                        }
                    }
                    i = j;
                }

                if (hasTie) {
                    groupState.inTiebreaker = true;
                    groupState.tieGroups = tieGroups;
                    console.log('🏁 Finals tied! Entering tiebreaker for tied players.');
                    return;
                }
            } else {
                // In tiebreaker - resolve within each tie group
                for (const tg of groupState.tieGroups) {
                    const groupPlayers = tg.players
                        .map(pos => groupState.players.find(p => p.position === pos))
                        .filter(p => p);
                    groupPlayers.sort((a, b) => (b.tiebreakerScore || 0) - (a.tiebreakerScore || 0));

                    for (let k = 0; k < groupPlayers.length; k++) {
                        const player = groupPlayers[k];
                        const rank = tg.startRank + k;
                        const node = this.getPlayerNode('finals', player.position);
                        if (node) {
                            node.classList.remove('active', 'eliminated', 'advancing', 'champion', 'second', 'third');
                            if (rank === 0) node.classList.add('champion');
                            else if (rank === 1) node.classList.add('second');
                            else if (rank === 2) node.classList.add('third');
                            const pointsEl = node.querySelector('.player-points');
                            if (pointsEl) pointsEl.textContent = medals[rank] || '';
                        }
                    }
                }
                groupState.inTiebreaker = false;
                groupState.tieGroups = null;
            }
        }
    }

    /**
     * Helper to advance a player to a target group
     */
    advancePlayerToGroup(player, fromGroup, targetGroup, targetPosition) {
        this.lightPath(`${fromGroup}-${player.position}`, `${targetGroup}-${targetPosition}`);

        const advancedPlayer = {
            name: player.name,
            position: targetPosition,
            rawScores: [null, null, null, null],
            points: 0,
            totalRawScore: 0
        };

        const targetState = this.tournamentState.groups[targetGroup];
        if (!targetState.players[targetPosition]) {
            targetState.players[targetPosition] = advancedPlayer;
        }

        this.updatePlayerNode(targetGroup, targetPosition, {
            name: player.name,
            score: 0,
            points: 0,
            rank: '-'
        });
    }

    /**
     * Update stage indicator text based on current active group
     */
    updateStageIndicator(groupName) {
        const indicatorMap = {
            A: '1/4决赛 第一场',
            B: '1/4决赛 第二场',
            C: '1/4决赛 第三场',
            D: '1/4决赛 第四场',
            E: '半决赛 第一场',
            F: '半决赛 第二场',
            finals: '决赛'
        };
        const indicatorEl = document.querySelector('.stage-indicator');
        if (indicatorEl) {
            indicatorEl.textContent = indicatorMap[groupName] || '1/4决赛';
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
                E: { players: [], scores: [], settled: false, advancing: [] },
                F: { players: [], scores: [], settled: false, advancing: [] }
            },
            finals: { players: [], scores: [], settled: false, inTiebreaker: false },
            currentStage: 'quarterfinal',
            currentActiveGroup: null
        };

        // Clear all player nodes (reset to 'TBD', 0, '-')
        const allGroups = ['A', 'B', 'C', 'D', 'E', 'F'];
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
            const node = this.getPlayerNode('finals', position);
            if (node) {
                node.classList.remove('champion', 'second', 'third');
            }
            this.setPlayerState('finals', position, '');
        }

        // Clear all path lighting
        this.clearAllPaths();

        // Reset tournament name
        const titleEl = document.querySelector('.tournament-title');
        if (titleEl) {
            const titleTextEl = titleEl.querySelector('.title-text');
            if (titleTextEl) titleTextEl.textContent = '淘汰赛';
        }

        // Reset stage indicator
        this.updateStageIndicator('A');
    }

    // ==========================================
    // DOM Helper Methods
    // ==========================================

    /**
     * Get player node element by group and position
     * @param {string} group - Group name (A, B, C, D, E, F, finals)
     * @param {number} position - Player position (0-3)
     * @returns {Element|null} Player node element
     */
    getPlayerNode(group, position) {
        return document.querySelector(`[data-group="${group}"][data-position="${position}"]`);
    }

    /**
     * Get SVG path element connecting two nodes
     * @param {string} from - Source node identifier (e.g., "A-0")
     * @param {string} to - Target node identifier (e.g., "E-0")
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
            if (pointsEl) pointsEl.textContent = data.points;
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
     * Highlight a group as active, clearing active from all other groups
     * @param {string} groupName - Group name to highlight
     */
    highlightGroup(groupName) {
        const allGroups = ['A', 'B', 'C', 'D', 'E', 'F', 'finals'];
        for (const g of allGroups) {
            const state = g === 'finals' ? this.tournamentState.finals : this.tournamentState.groups[g];
            if (!state || !state.players) continue;
            for (const player of state.players) {
                if (player) {
                    const node = this.getPlayerNode(g, player.position);
                    if (node) node.classList.remove('active');
                }
            }
        }

        const targetState = groupName === 'finals' ? this.tournamentState.finals : this.tournamentState.groups[groupName];
        if (targetState && targetState.players) {
            for (const player of targetState.players) {
                if (player) {
                    this.setPlayerState(groupName, player.position, 'active');
                }
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tournament = new TournamentApp();
});
