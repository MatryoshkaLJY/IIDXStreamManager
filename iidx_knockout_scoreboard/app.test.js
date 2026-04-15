/**
 * Tests for knockout tournament scoreboard app.js
 */
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const appCode = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');

function createApp() {
    const dom = new JSDOM(html, { runScripts: 'dangerously', url: 'http://localhost' });
    dom.window.eval(appCode);
    // Trigger DOMContentLoaded so app.js initializes window.tournament
    const event = new dom.window.Event('DOMContentLoaded');
    dom.window.document.dispatchEvent(event);
    return dom.window.tournament;
}

function assert(cond, msg) {
    if (!cond) throw new Error(msg);
}

// Test 1: E/F progression mapping from A-D
{
    const app = createApp();
    app.handleInit({
        tournamentName: 'Test',
        groups: {
            A: ['PA1', 'PA2', 'PA3', 'PA4'],
            B: ['PB1', 'PB2', 'PB3', 'PB4'],
            C: ['PC1', 'PC2', 'PC3', 'PC4'],
            D: ['PD1', 'PD2', 'PD3', 'PD4']
        }
    });

    // Score group A: PA1 1st, PA2 2nd
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 1, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 2, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 3, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 4, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});

    assert(app.tournamentState.groups.E.players[0]?.name === 'PA1', 'A 1st should go to E1');
    assert(app.tournamentState.groups.F.players[0]?.name === 'PA2', 'A 2nd should go to F1');

    // Score group B: PB1 1st, PB2 2nd
    app.handleScore({ stage: 'quarterfinal', group: 'B', round: 1, scores: [
        { player: 'PB1', score: 400 }, { player: 'PB2', score: 300 }, { player: 'PB3', score: 200 }, { player: 'PB4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'B', round: 2, scores: [
        { player: 'PB1', score: 400 }, { player: 'PB2', score: 300 }, { player: 'PB3', score: 200 }, { player: 'PB4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'B', round: 3, scores: [
        { player: 'PB1', score: 400 }, { player: 'PB2', score: 300 }, { player: 'PB3', score: 200 }, { player: 'PB4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'B', round: 4, scores: [
        { player: 'PB1', score: 400 }, { player: 'PB2', score: 300 }, { player: 'PB3', score: 200 }, { player: 'PB4', score: 100 }
    ]});

    assert(app.tournamentState.groups.F.players[1]?.name === 'PB1', 'B 1st should go to F2');
    assert(app.tournamentState.groups.E.players[1]?.name === 'PB2', 'B 2nd should go to E2');

    console.log('PASS: E/F progression mapping');
}

// Test 2: Group sorting by PT desc then total raw score desc
{
    const app = createApp();
    app.handleInit({
        tournamentName: 'Test',
        groups: { A: ['P1', 'P2', 'P3', 'P4'], B: [], C: [], D: [] }
    });
    // Round1: P1=1st(2), P2=2nd(1). Round2: P1=2nd(1), P2=1st(2). Round3: P1=2nd(1), P2=1st(2). Round4: P1=1st(2), P2=2nd(1).
    // P1=6pts, total=400. P2=6pts, total=420. P2 should win on raw score.
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 1, scores: [
        { player: 'P1', score: 100 }, { player: 'P2', score: 100 }, { player: 'P3', score: 50 }, { player: 'P4', score: 50 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 2, scores: [
        { player: 'P1', score: 100 }, { player: 'P2', score: 120 }, { player: 'P3', score: 50 }, { player: 'P4', score: 50 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 3, scores: [
        { player: 'P1', score: 100 }, { player: 'P2', score: 120 }, { player: 'P3', score: 50 }, { player: 'P4', score: 50 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 4, scores: [
        { player: 'P1', score: 100 }, { player: 'P2', score: 100 }, { player: 'P3', score: 50 }, { player: 'P4', score: 50 }
    ]});
    const container = app.getPlayerNode('A', 0).parentElement;
    const nodes = Array.from(container.querySelectorAll('[data-group="A"]'));
    const namesInDom = nodes.map(n => n.querySelector('.player-name').textContent);
    assert(namesInDom[0] === 'P2', 'P2 should be first in DOM due to higher raw score, got: ' + namesInDom.join(', '));
    assert(namesInDom[1] === 'P1', 'P1 should be second in DOM');
    console.log('PASS: group sorting by PT then total raw score');
}

// Test 3: Auto-advance after non-final settlement
{
    const app = createApp();
    app.handleInit({
        tournamentName: 'Test',
        groups: { A: ['PA1', 'PA2', 'PA3', 'PA4'], B: ['PB1', 'PB2', 'PB3', 'PB4'], C: [], D: [] }
    });
    assert(app.tournamentState.currentActiveGroup === 'A', 'Initial active group should be A');

    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 1, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 2, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 3, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});
    app.handleScore({ stage: 'quarterfinal', group: 'A', round: 4, scores: [
        { player: 'PA1', score: 400 }, { player: 'PA2', score: 300 }, { player: 'PA3', score: 200 }, { player: 'PA4', score: 100 }
    ]});

    // After auto-settle, should auto-advance to B
    assert(app.tournamentState.currentActiveGroup === 'B', 'After settling A, active group should auto-advance to B');
    console.log('PASS: auto-advance after settlement');
}

// Test 4: Finals tiebreaker
{
    const app = createApp();
    app.handleInit({
        tournamentName: 'Test',
        groups: { A: ['A1', 'A2', 'A3', 'A4'], B: ['B1', 'B2', 'B3', 'B4'], C: ['C1', 'C2', 'C3', 'C4'], D: ['D1', 'D2', 'D3', 'D4'] }
    });
    // Fill all groups and advance to finals
    for (const g of ['A', 'B', 'C', 'D']) {
        for (let r = 1; r <= 4; r++) {
            app.handleScore({ stage: 'quarterfinal', group: g, round: r, scores: [
                { player: g + '1', score: 400 }, { player: g + '2', score: 300 }, { player: g + '3', score: 200 }, { player: g + '4', score: 100 }
            ]});
        }
    }
    for (const g of ['E', 'F']) {
        for (let r = 1; r <= 4; r++) {
            app.handleScore({ stage: 'semifinal', group: g, round: r, scores: [
                { player: app.tournamentState.groups[g].players[0]?.name, score: 400 },
                { player: app.tournamentState.groups[g].players[1]?.name, score: 300 },
                { player: app.tournamentState.groups[g].players[2]?.name, score: 200 },
                { player: app.tournamentState.groups[g].players[3]?.name, score: 100 }
            ].filter(x => x.player) });
        }
    }

    // Now finals: make two players tie in PT
    const finals = app.tournamentState.finals.players;
    assert(finals.length >= 2, 'Should have finalists');
    // Simulate tied points by scoring rounds where two players tie
    app.handleScore({ stage: 'final', group: 'finals', round: 1, scores: finals.map((p, i) => ({ player: p.name, score: i < 2 ? 100 : 50 })) });
    app.handleScore({ stage: 'final', group: 'finals', round: 2, scores: finals.map((p, i) => ({ player: p.name, score: i < 2 ? 100 : 50 })) });
    app.handleScore({ stage: 'final', group: 'finals', round: 3, scores: finals.map((p, i) => ({ player: p.name, score: i < 2 ? 100 : 50 })) });
    app.handleScore({ stage: 'final', group: 'finals', round: 4, scores: finals.map((p, i) => ({ player: p.name, score: i < 2 ? 100 : 50 })) });

    app.handleSettle({ stage: 'final', group: 'finals' });

    assert(app.tournamentState.finals.inTiebreaker === true, 'Should enter tiebreaker when PT is tied');
    console.log('PASS: finals tiebreaker detection');
}

// Test 5: Medal classes use .silver and .bronze
{
    const app = createApp();
    app.handleInit({
        tournamentName: 'Test',
        groups: { A: ['A1', 'A2', 'A3', 'A4'], B: ['B1', 'B2', 'B3', 'B4'], C: ['C1', 'C2', 'C3', 'C4'], D: ['D1', 'D2', 'D3', 'D4'] }
    });
    for (const g of ['A', 'B', 'C', 'D']) {
        for (let r = 1; r <= 4; r++) {
            app.handleScore({ stage: 'quarterfinal', group: g, round: r, scores: [
                { player: g + '1', score: 400 }, { player: g + '2', score: 300 }, { player: g + '3', score: 200 }, { player: g + '4', score: 100 }
            ]});
        }
    }
    for (const g of ['E', 'F']) {
        for (let r = 1; r <= 4; r++) {
            app.handleScore({ stage: 'semifinal', group: g, round: r, scores: [
                { player: app.tournamentState.groups[g].players[0]?.name, score: 400 },
                { player: app.tournamentState.groups[g].players[1]?.name, score: 300 },
                { player: app.tournamentState.groups[g].players[2]?.name, score: 200 },
                { player: app.tournamentState.groups[g].players[3]?.name, score: 100 }
            ].filter(x => x.player) });
        }
    }

    // Score finals with distinct PTs (no ties)
    const finals = app.tournamentState.finals.players;
    // Round 1: A1=1st(2), B2=2nd(1), A2=3rd(0), B1=4th(0)
    app.handleScore({ stage: 'final', group: 'finals', round: 1, scores: finals.map((p, i) => ({ player: p.name, score: [100, 80, 60, 40][i] })) });
    // Round 2: A1=1st(2), B2=2nd(1), A2=3rd(0), B1=4th(0)
    app.handleScore({ stage: 'final', group: 'finals', round: 2, scores: finals.map((p, i) => ({ player: p.name, score: [100, 80, 60, 40][i] })) });
    // Round 3: A1=1st(2), A2=2nd(1), B2=3rd(0), B1=4th(0)
    app.handleScore({ stage: 'final', group: 'finals', round: 3, scores: finals.map((p, i) => ({ player: p.name, score: [100, 60, 80, 40][i] })) });
    // Round 4: A1=1st(2), B2=2nd(1), A2=3rd(0), B1=4th(0)
    app.handleScore({ stage: 'final', group: 'finals', round: 4, scores: finals.map((p, i) => ({ player: p.name, score: [100, 80, 60, 40][i] })) });

    app.handleSettle({ stage: 'final', group: 'finals' });

    const nodes = finals.map((p, i) => app.getPlayerNode('finals', i));
    assert(nodes[0].classList.contains('champion'), '1st place should have .champion');
    assert(nodes[1].classList.contains('silver'), '2nd place should have .silver');
    assert(nodes[2].classList.contains('bronze'), '3rd place should have .bronze');
    console.log('PASS: medal CSS classes');
}

// Test 6: CSS contains .silver and .bronze rules
{
    const css = fs.readFileSync(path.join(__dirname, 'style.css'), 'utf8');
    assert(css.includes('.silver'), 'CSS should contain .silver rule');
    assert(css.includes('.bronze'), 'CSS should contain .bronze rule');
    console.log('PASS: silver/bronze CSS present');
}

console.log('\nAll tests passed!');
