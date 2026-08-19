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
        this.wsUrl = `ws://${location.hostname || '127.0.0.1'}:8081`;

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
            const titleTextEl = document.querySelector('.title-text');
            if (titleTextEl) titleTextEl.textContent = data.tournamentName;
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

        // 起始阶段赛制：init 载荷带 startGroup（'E' = 8 人 EF 组起，'finals' = 4 人直接决赛）
        const startGroup = data.startGroup || null;
        const efOnly = startGroup === 'E';
        const finalOnly = startGroup === 'finals';
        const container = document.querySelector('.tournament-container');
        if (efOnly) {
            for (const groupName of ['E', 'F']) {
                const playerNames = data.groups[groupName];
                if (playerNames && Array.isArray(playerNames) && playerNames.length === 4) {
                    this.tournamentState.groups[groupName].players = playerNames.map((name, index) => ({
                        name: name,
                        position: index,
                        rawScores: [null, null, null, null],
                        points: 0,
                        totalRawScore: 0
                    }));

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
            // 隐藏 A-D 小组赛区域
            if (container) container.classList.add('ef-only');
        } else {
            // Initialize empty semifinal groups (E, F)
            this.tournamentState.groups.E.players = [];
            this.tournamentState.groups.F.players = [];
        }

        // Initialize finals
        if (finalOnly) {
            const finalistNames = data.groups['finals'];
            if (finalistNames && Array.isArray(finalistNames) && finalistNames.length === 4) {
                this.tournamentState.finals.players = finalistNames.map((name, index) => ({
                    name: name,
                    position: index,
                    rawScores: [null, null, null, null],
                    points: 0,
                    totalRawScore: 0,
                    tiebreakerScore: 0
                }));

                finalistNames.forEach((name, position) => {
                    this.updatePlayerNode('finals', position, {
                        name: name,
                        score: 0,
                        points: 0,
                        rank: '-'
                    });
                });
            }
            // 隐藏 A-F 前置阶段区域
            if (container) container.classList.add('final-only');
        } else {
            this.tournamentState.finals.players = [];
        }
        this.tournamentState.finals.inTiebreaker = false;

        // Clear any existing path lighting
        this.clearAllPaths();

        if (efOnly) {
            this.tournamentState.currentStage = 'semifinal';
            this.tournamentState.currentActiveGroup = 'E';
            this.highlightGroup('E');
            this.updateStageIndicator('E');
        } else if (finalOnly) {
            this.tournamentState.currentStage = 'final';
            this.tournamentState.currentActiveGroup = 'finals';
            this.highlightGroup('finals');
            this.updateStageIndicator('finals');
        } else {
            this.tournamentState.currentStage = 'quarterfinal';
            this.tournamentState.currentActiveGroup = 'A';
            this.highlightGroup('A');
            this.updateStageIndicator('A');
        }
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

        // Validate round（常规局 1-4，加赛局从 5 开始递增）
        if (round < 1) {
            console.error('SCORE command: round must be >= 1');
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

        // Calculate ranks with competition ranking（同分同名次：并列第一均为第 1 名）
        const ranks = new Map();
        for (const s of scores) {
            ranks.set(s.player, 1 + scores.filter(o => o.score > s.score).length);
        }

        // Update each player's data
        for (const scoreData of scores) {
            const playerName = scoreData.player;
            const rawScore = scoreData.score;
            const rank = ranks.get(playerName);
            const points = this.calculatePoints(rank);

            // Find player in group
            const player = groupState.players.find(p => p && p.name === playerName);
            if (player) {
                if (groupState.inTiebreaker) {
                    // 加赛局：只累计加赛分，不影响常规局数据
                    player.tiebreakerScore = (player.tiebreakerScore || 0) + rawScore;
                } else {
                    // Store raw score for this round (round is 1-indexed, array is 0-indexed)
                    player.rawScores[round - 1] = rawScore;
                    player.totalRawScore = (player.totalRawScore || 0) + rawScore;
                    // Add points for this round
                    player.points += points;
                }

                // Update DOM（加赛期间显示加赛累计分）
                this.updatePlayerNode(group, player.position, {
                    score: groupState.inTiebreaker ? player.tiebreakerScore : player.totalRawScore,
                    points: player.points,
                    rank: rank
                });
            }
        }

        // Auto-settle after 4 rounds for non-final groups（加赛期间每次收到分数都重新结算）
        if (stage !== 'final' && !groupState.settled &&
            (groupState.scores.length === 4 || groupState.inTiebreaker)) {
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

        // 加赛结算：各并列组内按加赛分定名次，仍平分的子组继续加赛（非决赛末位并列除外）
        if (groupState.inTiebreaker) {
            if (this.resolveTiebreaker(groupState, stage)) {
                console.log(`🏁 ${stage} Group ${group} still tied, playoff continues.`);
                return;
            }
            groupState.inTiebreaker = false;
            groupState.tieGroups = null;
        }

        // Sort players based on stage rules
        let sortedPlayers;
        if (stage === 'final') {
            // 决赛：只按 PT 排名
            sortedPlayers = [...groupState.players].sort((a, b) => {
                return b.points - a.points;
            });
        } else {
            // A-F groups: sort by PT then totalRawScore
            sortedPlayers = [...groupState.players].sort((a, b) => {
                if (b.points !== a.points) {
                    return b.points - a.points; // Higher points first
                }
                return b.totalRawScore - a.totalRawScore; // Higher raw score as tiebreaker
            });
        }

        // 首次结算：检测并列组（决赛看 PT；A-F 看 PT + 总 EX），有则进入加赛。
        // 非决赛只需决出前两名：不跨越出线线（第 2/3 名之间）的并列不加赛——
        // 头名并列（都出线）与第 3 名及以后的并列（都淘汰）均按当前排序落位
        if (!groupState.tiebreakPlacement) {
            const tieGroups = stage === 'final'
                ? this.findTieGroups(sortedPlayers, p => p.points)
                : this.findTieGroups(sortedPlayers, p => `${p.points}|${p.totalRawScore}`)
                      .filter(tg => tg.startRank < 2 && tg.startRank + tg.players.length > 2);
            if (tieGroups.length > 0) {
                groupState.inTiebreaker = true;
                groupState.tieGroups = tieGroups;
                for (const tg of tieGroups) {
                    // 并列选手保持 active，等待加赛
                    for (const pos of tg.players) {
                        this.setPlayerState(stage === 'final' ? 'finals' : group, pos, 'active');
                    }
                }
                console.log(`🏁 ${stage} Group ${group} tied! Entering tiebreaker for tied players.`);
                return;
            }
        } else {
            // 应用加赛结果：替换各并列区间的位置
            sortedPlayers = sortedPlayers.map((p, i) => groupState.tiebreakPlacement[i] || p);
        }

        groupState.settled = true;

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

            // Reorder DOM nodes to match sorted order
            this.reorderGroupNodes(group, sortedPlayers);

            // Store advancing players in group state
            groupState.advancing = advancing.map(p => ({ ...p }));

            // Auto-advance to next group
            this.handleContinue();

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
            // stage === 'final'：名次全部决出（含加赛结果），发放奖牌
            const medals = ['🥇', '🥈', '🥉', ''];
            sortedPlayers.forEach((player, i) => {
                const node = this.getPlayerNode('finals', player.position);
                if (node) {
                    node.classList.remove('active', 'eliminated', 'advancing', 'champion', 'silver', 'bronze');
                    if (i === 0) node.classList.add('champion');
                    else if (i === 1) node.classList.add('silver');
                    else if (i === 2) node.classList.add('bronze');
                    const pointsEl = node.querySelector('.player-points');
                    if (pointsEl) pointsEl.textContent = medals[i] || '';
                }
            });
        }
    }

    /**
     * Find tied groups in sorted players（key 相同的相邻选手为一组）
     * @param {Array} sortedPlayers - 已排序的选手数组
     * @param {Function} keyFn - 并列判定键
     * @returns {Array} [{startRank, players: [position, ...]}]
     */
    findTieGroups(sortedPlayers, keyFn) {
        const groups = [];
        let i = 0;
        while (i < sortedPlayers.length) {
            let j = i + 1;
            while (j < sortedPlayers.length && keyFn(sortedPlayers[j]) === keyFn(sortedPlayers[i])) {
                j++;
            }
            if (j - i > 1) {
                groups.push({ startRank: i, players: sortedPlayers.slice(i, j).map(p => p.position) });
            }
            i = j;
        }
        return groups;
    }

    /**
     * 加赛结算：各并列组内按加赛分排序，仍平分的子组保留为未决组。
     * 已决出的位置写入 groupState.tiebreakPlacement（名次下标 -> 选手）。
     * 非决赛只需决出前两名：不跨越出线线（第 2/3 名之间）的并列子组按加赛分顺序落位，不再加赛。
     * @param {Object} groupState - 组状态（需含 tieGroups / players）
     * @param {string} stage - 阶段（quarterfinal / semifinal / final）
     * @returns {boolean} true 表示仍有未决并列，需要继续加赛
     */
    resolveTiebreaker(groupState, stage) {
        const pending = [];
        const placement = groupState.tiebreakPlacement || {};
        for (const tg of groupState.tieGroups) {
            const groupPlayers = tg.players
                .map(pos => groupState.players.find(p => p.position === pos))
                .filter(p => p);
            groupPlayers.sort((a, b) => (b.tiebreakerScore || 0) - (a.tiebreakerScore || 0));

            let i = 0;
            let rank = tg.startRank;
            while (i < groupPlayers.length) {
                let j = i + 1;
                while (j < groupPlayers.length &&
                       (groupPlayers[j].tiebreakerScore || 0) === (groupPlayers[i].tiebreakerScore || 0)) {
                    j++;
                }
                const sub = groupPlayers.slice(i, j);
                if (sub.length > 1 && (stage === 'final' || (rank < 2 && rank + sub.length > 2))) {
                    pending.push({ startRank: rank, players: sub.map(p => p.position) });
                } else {
                    // 单人或（非决赛）不跨出线线的并列：按当前加赛分顺序落位，不再加赛
                    sub.forEach((p, k) => { placement[rank + k] = p; });
                }
                rank += sub.length;
                i = j;
            }
        }
        groupState.tiebreakPlacement = placement;
        if (pending.length > 0) {
            groupState.tieGroups = pending;
            return true;
        }
        return false;
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
                node.classList.remove('champion', 'silver', 'bronze');
            }
            this.setPlayerState('finals', position, '');
        }

        // Clear all path lighting
        this.clearAllPaths();

        // Reset tournament name
        const titleTextEl = document.querySelector('.title-text');
        if (titleTextEl) titleTextEl.textContent = '16人淘汰赛';

        // 恢复完整 16 人布局（清除 EF/决赛赛制的区域隐藏）
        const container = document.querySelector('.tournament-container');
        if (container) container.classList.remove('ef-only', 'final-only');

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
     * Reorder DOM nodes within a group to match sorted player order
     * @param {string} group - Group name
     * @param {Array} sortedPlayers - Players in desired display order
     */
    reorderGroupNodes(group, sortedPlayers) {
        const container = document.querySelector('.tournament-tree');
        if (!container) return;

        const nodes = sortedPlayers.map(p => this.getPlayerNode(group, p.position)).filter(n => n);
        const label = container.querySelector(`.group-${group.toLowerCase()}-label`);

        if (!label) return;

        // Collect all group nodes and move them after the label in sorted order.
        // Insert in reverse so the first sorted node ends up first after the label.
        for (let i = nodes.length - 1; i >= 0; i--) {
            label.parentNode.insertBefore(nodes[i], label.nextSibling);
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
