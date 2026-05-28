import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Bell, ShieldAlert, Bot, Flag, Clock, ExternalLink, RefreshCw } from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export default function SportsBettingDashboard() {
  // Stany danych z API
  const [matches, setMatches] = useState([]);
  const [topAnomalies, setTopAnomalies] = useState([]);
  const [timeData, setTimeData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Stany filtrów i widoków
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // all, intel, potential, trash
  const [timePeriod, setTimePeriod] = useState(30);
  const [topAnomalyFilter, setTopAnomalyFilter] = useState({ league: 'All', sport: 'All', limit: 10 });
  
  // UI i Modale
  const [notifications, setNotifications] = useState([]);
  // Stan wiadomości i inputu (zostaje bez zmian)
  const [showAiChat, setShowAiChat] = useState(false);
  const [aiMessages, setAiMessages] = useState([
    { sender: 'bot', text: 'Cześć! Jestem prawdziwym Agentem AI podłączonym do modelu Gemini. W czym mogę Ci pomóc?' }
  ]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showModal, setShowModal] = useState({ show: false, url: '' });
  const [showTimeModal, setShowTimeModal] = useState(false);
  const [riskSuggestion, setRiskSuggestion] = useState(null);

  const callGeminiReal = async (userPrompt) => {
  setAiLoading(true);
  
  // Budujemy kontekst systemowy, żeby model wiedział, w jakiej aplikacji się znajduje
  // Przekazujemy mu aktualne top anomalie, które pobraliśmy z SQLite!
  const databaseContext = `
    Jesteś asystentem AI w aplikacji bukmacherskiej "SmartBet Analytics". 
    Aktualne anomalie wykryte w bazie SQLite to: ${JSON.stringify(topAnomalies)}.
    Użytkownik pyta o:
  `;

  try {
    const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-goog-api-key": "" // <-- Wklej tutaj swój klucz API
      },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              { text: databaseContext + userPrompt }
            ]
          }
        ]
      })
    });

    if (!response.ok) throw new Error("Problem z odpowiedzią od API Gemini");
    
    const json = await response.json();
    // Parsowanie struktury odpowiedzi Gemini
    const botReply = json.candidates[0].content.parts[0].text;
    
    // Dodanie odpowiedzi bota do okna czatu
    setAiMessages(prev => [...prev, { sender: 'bot', text: botReply }]);

  } catch (error) {
    console.error("Błąd Gemini API:", error);
    setAiMessages(prev => [...prev, { sender: 'bot', text: "Przepraszam, wystąpił problem podczas połączenia z moim mózgiem AI. Sprawdź poprawność klucza API." }]);
  } finally {
    setAiLoading(false);
  }
};

// Funkcja wywoływana po kliknięciu "Wyślij" przez użytkownika
const handleSendAiMessage = () => {
  if (!aiInput.trim() || aiLoading) return;

  const userQuery = aiInput;
  // 1. Dodaj tekst użytkownika do czatu
  setAiMessages(prev => [...prev, { sender: 'user', text: userQuery }]);
  setAiInput('');

  // 2. Wywołaj zapytanie do sieci neuronowej
  callGeminiReal(userQuery);
};

  // 1. Pobieranie meczów i kursów z API
  const fetchMatches = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/matches`);
      if (!response.ok) throw new Error('Błąd pobierania meczów');
      const data = await response.json();
      
      // Sprawdzanie czy pojawiły się nowe anomalie w stosunku do poprzedniego stanu (Zasada LIVE 1m)
      if (matches.length > 0) {
        data.forEach(newMatch => {
          const oldMatch = matches.find(m => m.id === newMatch.id);
          if (oldMatch && newMatch.is_live) {
            const diff = Math.abs(newMatch.current_odds.win1 - oldMatch.current_odds.win1) / oldMatch.current_odds.win1;
            if (diff > 0.15) {
              // Zmiana tekstu na niebieski (obsługiwane flagą w obiekcie)
              newMatch.colorBlue = true;
              setNotifications(prev => [
                { id: Date.now(), message: `Kurs w meczu LIVE ${newMatch.home} zmienił się o >15%!`, type: 'live-change' },
                ...prev
              ]);
            }
          }
        });
      }
      setMatches(data);
    } catch (error) {
      printError("matches", error);
    } finally {
      setLoading(false);
    }
  };

  // 2. Pobieranie TOP anomalii z uwzględnieniem filtrów
  const fetchAnomalies = async () => {
    try {
      const { sport, league, limit } = topAnomalyFilter;
      const url = `${API_BASE_URL}/anomalies?sport=${sport}&league=${league}&limit=${limit}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Błąd pobierania anomalii');
      const data = await response.json();
      setTopAnomalies(data);
      
      // Powiadomienie na widoku głównym o krytycznej anomalii (>20%)
      const criticalAnomaly = data.find(a => parseFloat(a.change) > 20);
      if (criticalAnomaly) {
        setNotifications(prev => [
          { id: Date.now(), message: `KRYTYCZNA ANOMALIA: ${criticalAnomaly.match} w ${criticalAnomaly.bookmaker} (${criticalAnomaly.change})!`, type: 'anomaly' },
          ...prev
        ]);
      }
    } catch (error) {
      printError("anomalies", error);
    }
  };

  // 3. Pobieranie danych do wykresu czasu
  const fetchTimeStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/user/time-stats?days=${timePeriod}`);
      if (!response.ok) throw new Error('Błąd pobierania statystyk czasu');
      const data = await response.json();
      setTimeData(data);
    } catch (error) {
      printError("time-stats", error);
    }
  };

  // 4. Aktualizacja flagi w bazie danych
  const handleFlagChange = async (matchId, newFlagType) => {
    try {
      const response = await fetch(`${API_BASE_URL}/flags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ match_id: matchId, flag_type: newFlagType })
      });
      if (!response.ok) throw new Error('Nie udało się zapisać flagi');
      
      // Aktualizujemy stan lokalny po pomyślnym zapisie w SQLite
      setMatches(prev => prev.map(m => m.id === matchId ? { ...m, flag: newFlagType } : m));
    } catch (error) {
      alert("Problem z bazą danych: " + error.message);
    }
  };

  // Pomocnicza funkcja logowania błędów w konsoli
  const printError = (target, err) => console.error(`[API Error] Połączenie z /api/${target} nie powiodło się. Upewnij się, że serwer FastAPI działa.`, err);

  // Hooki efektów do synchronizacji z backendem
  useEffect(() => {
    fetchMatches();
    // Odświeżanie kursów w meczach na żywo co 1 minutę (60000 ms)
    const interval = setInterval(fetchMatches, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchAnomalies();
  }, [topAnomalyFilter]);

  useEffect(() => {
    if (showTimeModal) fetchTimeStats();
  }, [showTimeModal, timePeriod]);


  // Obsługa linków zewnętrznych z oknem potwierdzenia
  const handleBetClick = (url) => {
    setShowModal({ show: true, url: url });
  };

  const confirmRedirect = () => {
    window.open(showModal.url, '_blank');
    setShowModal({ show: false, url: '' });
  };

  const checkRiskMitigation = (match) => {
    setRiskSuggestion({
      original: `Czyste zwycięstwo ${match.home} (Kurs: ${match.current_odds.win1})`,
      alternative: `Zwycięstwo ${match.home} lub Remis [1X] (Kurs: ${(match.current_odds.win1 * 0.72).toFixed(2)})`,
      desc: "Zmniejszasz ryzyko przegranej o ok. 33%, zachowując opłacalność kuponu."
    });
  };

  if (loading) {
    return <div style={{ color: '#fff', textAlign: 'center', marginTop: '100px', fontSize: '20px' }}>Ładowanie danych ze SmartBet API...</div>;
  }

  return (
    <div style={{ backgroundColor: '#111827', color: '#f3f4f6', minHeight: '100vh', padding: '24px', fontFamily: 'sans-serif' }}>
      
      {/* NAGŁÓWEK & STATYSTYKI CZASU */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #374151', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 'bold', color: '#60a5fa' }}>SmartBet Analytics</h1>
          <p style={{ color: '#9ca3af' }}>Dane połączone bezpośrednio z bazą danych SQLite</p>
        </div>
        
        <div 
          onClick={() => setShowTimeModal(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#1f2937', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer', border: '1px solid #4b5563' }}
        >
          <Clock size={20} color="#10b981" />
          <div>
            <div style={{ fontSize: '12px', color: '#9ca3af' }}>Czas sesji (Analiza 30-365 dni)</div>
            <div style={{ fontWeight: 'bold', color: '#10b981' }}>Kliknij, aby zobaczyć wykres</div>
          </div>
        </div>
      </header>

      {/* POWIADOMIENIA O ANOMALIACH */}
      {notifications.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          {notifications.map(n => (
            <div key={n.id} style={{ backgroundColor: n.type === 'anomaly' ? '#7f1d1d' : '#1e3a8a', borderLeft: '4px solid #ef4444', padding: '12px', borderRadius: '4px', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ShieldAlert color="#f87171" />
              <span>{n.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* GŁÓWNY UKŁAD STRONY */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '24px' }}>
        
        {/* LEWA KOLUMNA: FILTRY, MECZE, SZCZEGÓŁY */}
        <div>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            {['all', 'intel', 'potential', 'trash'].map(tab => (
              <button 
                key={tab} 
                onClick={() => setActiveTab(tab)}
                style={{ padding: '8px 16px', borderRadius: '6px', border: 'none', backgroundColor: activeTab === tab ? '#3b82f6' : '#1f2937', color: '#fff', cursor: 'pointer' }}
              >
                {tab === 'all' && 'Wszystkie'}
                {tab === 'intel' && '⭐ Interesujące'}
                {tab === 'potential' && '⏳ Potencjalne'}
                {tab === 'trash' && '❌ Nieinteresujące'}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {matches
              .filter(m => activeTab === 'all' || m.flag === activeTab)
              .map(match => (
                <div key={match.id} style={{ backgroundColor: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '12px', backgroundColor: '#374151', padding: '4px 8px', borderRadius: '4px' }}>{match.league}</span>
                    {match.is_live ? (
                      <span style={{ fontSize: '12px', color: '#ef4444', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <RefreshCw size={12} /> LIVE (Auto-refresh 1m)
                      </span>
                    ) : null}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '18px' }}>{match.home} vs {match.away}</h3>
                      <div style={{ display: 'flex', gap: '12px', marginTop: '4px', fontSize: '12px', color: '#9ca3af' }}>
                        <div>Forma {match.home}: {match.last5_home?.join('-') || 'Brak'}</div>
                        <div>Forma {match.away}: {match.last5_away?.join('-') || 'Brak'}</div>
                      </div>
                    </div>

                    {/* PRZYCISKI FLAGOWANIA Z SYNCHRONIZACJĄ SQLITE */}
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button onClick={() => handleFlagChange(match.id, match.flag === 'intel' ? 'all' : 'intel')} title="Interesujące" style={{ background: match.flag === 'intel' ? '#eab308' : '#374151', border: 'none', padding: '6px', borderRadius: '4px', cursor: 'pointer', color: '#fff' }}><Flag size={14} /></button>
                      <button onClick={() => handleFlagChange(match.id, match.flag === 'potential' ? 'all' : 'potential')} title="Rozważam" style={{ background: match.flag === 'potential' ? '#3b82f6' : '#374151', border: 'none', padding: '6px', borderRadius: '4px', cursor: 'pointer', color: '#fff' }}><Flag size={14} /></button>
                      <button onClick={() => handleFlagChange(match.id, match.flag === 'trash' ? 'all' : 'trash')} title="Nie interesuje mnie" style={{ background: match.flag === 'trash' ? '#ef4444' : '#374151', border: 'none', padding: '6px', borderRadius: '4px', cursor: 'pointer', color: '#fff' }}><Flag size={14} /></button>
                    </div>
                  </div>

                  {/* DYNAMICZNE KURSY */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginTop: '16px' }}>
                    <div onClick={() => checkRiskMitigation(match)} style={{ backgroundColor: '#2d3748', padding: '10px', borderRadius: '6px', cursor: 'pointer', textAlign: 'center' }}>
                      <div style={{ fontSize: '12px', color: '#9ca3af' }}>1 ({match.bookmaker})</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: match.colorBlue ? '#60a5fa' : '#fff' }}>{match.current_odds?.win1}</div>
                    </div>
                    <div style={{ backgroundColor: '#2d3748', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '12px', color: '#9ca3af' }}>X</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{match.current_odds?.draw}</div>
                    </div>
                    <div style={{ backgroundColor: '#2d3748', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '12px', color: '#9ca3af' }}>2</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{match.current_odds?.win2}</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                    <button onClick={() => setSelectedMatch(match)} style={{ flex: 1, backgroundColor: '#4b5563', color: '#fff', border: 'none', padding: '8px', borderRadius: '6px', cursor: 'pointer' }}>
                      Wyświetl specyficzne kupony (faule itp.)
                    </button>
                    <button onClick={() => handleBetClick(match.url)} style={{ backgroundColor: '#10b981', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      Przejdź na stronę <ExternalLink size={14} />
                    </button>
                  </div>
                </div>
            ))}
          </div>

          {/* RYZYKO ALTERNATYWNE */}
          {riskSuggestion && (
            <div style={{ backgroundColor: '#064e3b', border: '1px solid #059669', padding: '16px', borderRadius: '8px', marginTop: '16px' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#34d399' }}>Sugestia optymalizacji ryzyka od systemu</h4>
              <p style={{ fontSize: '14px' }}>Zamiast czystego typu wybierz alternatywę: <strong style={{ color: '#34d399' }}>{riskSuggestion.alternative}</strong></p>
              <span style={{ fontSize: '12px', color: '#a7f3d0' }}>{riskSuggestion.desc}</span>
            </div>
          )}

          {/* WIDOK SZCZEGÓŁOWY (FAULE/KARTKI) */}
          {selectedMatch && (
            <div style={{ backgroundColor: '#1f2937', padding: '20px', borderRadius: '8px', marginTop: '24px', border: '1px solid #3b82f6' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <h3>Specyficzne oferty dla meczu: {selectedMatch.home} - {selectedMatch.away}</h3>
                <button onClick={() => setSelectedMatch(null)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '16px' }}>Zamknij</button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { name: "Liczba fauli powyżej 21.5", odd: 1.85, bookmaker: selectedMatch.bookmaker },
                  { name: "Żółte kartki powyżej 3.5", odd: 1.65, bookmaker: selectedMatch.bookmaker }
                ].map((spec, idx) => (
                  <div key={idx} style={{ backgroundColor: '#2d3748', padding: '12px', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{spec.name} <strong>({spec.bookmaker})</strong></span>
                    <button onClick={() => handleBetClick(selectedMatch.url)} style={{ backgroundColor: '#3b82f6', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer' }}>
                      Kurs {spec.odd} | Postaw kupon
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* PRAWA KOLUMNA: TABELA TOP 10 ANOMALII */}
        <aside style={{ backgroundColor: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151', height: 'fit-content' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '18px' }}>TOP Anomalii rynkowych</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px' }}>
            <select 
              onChange={(e) => setTopAnomalyFilter(p => ({...p, league: e.target.value}))}
              style={{ backgroundColor: '#374151', color: '#fff', border: 'none', padding: '6px', borderRadius: '4px' }}
            >
              <option value="All">Wszystkie ligi</option>
              <option value="Ekstraklasa">Ekstraklasa</option>
              <option value="La Liga">La Liga</option>
              <option value="Premier League">Premier League</option>
            </select>
            <select 
              onChange={(e) => setTopAnomalyFilter(p => ({...p, limit: parseInt(e.target.value)}))}
              style={{ backgroundColor: '#374151', color: '#fff', border: 'none', padding: '6px', borderRadius: '4px' }}
            >
              <option value="5">Top 5</option>
              <option value="10">Top 10</option>
              <option value="20">Top 20</option>
            </select>
          </div>

          {/* Renderowanie listy z wymuszonym suwakiem/scrollem dla >10 pozycji */}
          <div style={{ maxHeight: '380px', overflowY: 'scroll', paddingRight: '4px', borderRight: '2px solid #4b5563' }}>
            {topAnomalies.map((anomaly) => (
              <div key={anomaly.id} style={{ padding: '8px', backgroundColor: '#2d3748', borderRadius: '4px', marginBottom: '6px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>{anomaly.match}</strong>
                  <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{anomaly.change}</span>
                </div>
                <div style={{ color: '#9ca3af', fontSize: '11px' }}>{anomaly.bookmaker} • {anomaly.league}</div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      {/* AGENT AI */}
      <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 1000 }}>
        {!showAiChat ? (
          <button onClick={() => setShowAiChat(true)} style={{ backgroundColor: '#3b82f6', color: '#fff', border: 'none', width: '60px', height: '60px', borderRadius: '50%', cursor: 'pointer', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}><Bot size={28} /></button>
        ) : (
          <div style={{ width: '350px', height: '400px', backgroundColor: '#1f2937', borderRadius: '12px', border: '1px solid #3b82f6', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ backgroundColor: '#3b82f6', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Bot size={20} /> <strong>Agent AI (Live Data)</strong></div>
              <button onClick={() => setShowAiChat(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '16px' }}>×</button>
            </div>
            <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {aiMessages.map((msg, i) => (
                <div key={i} style={{ alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start', backgroundColor: msg.sender === 'user' ? '#3b82f6' : '#374151', padding: '8px 12px', borderRadius: '8px', maxWidth: '80%', fontSize: '14px' }}>{msg.text}</div>
              ))}
            </div>
            <div style={{ padding: '8px', borderTop: '1px solid #374151', display: 'flex', gap: '8px' }}>
              <input type="text" value={aiInput} onChange={(e) => setAiInput(e.target.value)} placeholder="Czy jest jakaś ciekawa anomalia?" style={{ flex: 1, backgroundColor: '#374151', border: 'none', padding: '8px', borderRadius: '4px', color: '#fff' }}/>
              <button 
                onClick={() => {
                  if(!aiInput) return;
                  setAiMessages(p => [...p, { sender: 'user', text: aiInput }]);
                  setTimeout(() => {
                    const topA = topAnomalies[0];
                    setAiMessages(p => [...p, { sender: 'bot', text: `Przeanalizowałem bazę SQLite. Największa wykryta obecnie anomalia to mecz ${topA ? topA.match : 'Ekstraklasy'} w bukmacherze ${topA ? topA.bookmaker : 'Betclic'} z odchyłką ${topA ? topA.change : '18.5%'}.` }]);
                  }, 600);
                  setAiInput('');
                }}
                style={{ backgroundColor: '#10b981', border: 'none', padding: '8px 12px', borderRadius: '4px', color: '#fff', cursor: 'pointer' }}
              >
                Wyślij
              </button>
            </div>
          </div>
        )}
      </div><div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 1000 }}>
    {!showAiChat ? (
      <button onClick={() => setShowAiChat(true)} style={{ backgroundColor: '#3b82f6', color: '#fff', border: 'none', width: '60px', height: '60px', borderRadius: '50%', cursor: 'pointer', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Bot size={28} />
      </button>
    ) : (
      <div style={{ width: '380px', height: '450px', backgroundColor: '#1f2937', borderRadius: '12px', border: '1px solid #3b82f6', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
        
        {/* Nagłówek okna */}
        <div style={{ backgroundColor: '#3b82f6', padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Bot size={20} /> <strong>Agent AI (Gemini 2.5 Live)</strong></div>
          <button onClick={() => setShowAiChat(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '18px', fontWeight: 'bold' }}>×</button>
        </div>
        
        {/* Okno wiadomości */}
        <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {aiMessages.map((msg, i) => (
            <div 
              key={i} 
              style={{ 
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start', 
                backgroundColor: msg.sender === 'user' ? '#3b82f6' : '#374151', 
                padding: '10px 14px', 
                borderRadius: '8px', 
                maxWidth: '85%', 
                fontSize: '14px',
                lineHeight: '1.4',
                whiteSpace: 'pre-wrap' // Zachowuje formatowanie nowej linii z LLM
              }}
            >
              {msg.text}
            </div>
          ))}
          
          {/* Wskaźnik pisania przez bota */}
          {aiLoading && (
            <div style={{ alignSelf: 'flex-start', backgroundColor: '#374151', padding: '10px 14px', borderRadius: '8px', fontSize: '14px', color: '#9ca3af' }}>
              <span className="animate-pulse">Agent analizuje bazę danych i generuje odpowiedź...</span>
            </div>
          )}
        </div>
        
        {/* Panel wprowadzania tekstu */}
        <div style={{ padding: '8px', borderTop: '1px solid #374151', display: 'flex', gap: '8px', backgroundColor: '#111827' }}>
          <input 
            type="text" 
            value={aiInput} 
            onChange={(e) => setAiInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendAiMessage()} // Obsługa wysyłki enterem
            placeholder="Napisz np.: Czy jest jakaś ciekawa anomalia?" 
            disabled={aiLoading}
            style={{ flex: 1, backgroundColor: '#374151', border: 'none', padding: '10px', borderRadius: '4px', color: '#fff', outline: 'none' }}
          />
          <button 
            onClick={handleSendAiMessage}
            disabled={aiLoading}
            style={{ backgroundColor: aiLoading ? '#4b5563' : '#10b981', border: 'none', padding: '10px 16px', borderRadius: '4px', color: '#fff', cursor: aiLoading ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
          >
            Wyślij
          </button>
        </div>

      </div>
    )}
  </div>

      {/* MODAL: PRZEJŚCIE DO BUKMACHERA */}
      {showModal.show && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 2000 }}>
          <div style={{ backgroundColor: '#1f2937', padding: '24px', borderRadius: '8px', width: '420px', textAlign: 'center', border: '1px solid #4b5563' }}>
            <h3 style={{ margin: '0 0 10px 0' }}>Czy chcesz przejść na stronę bukmachera?</h3>
            <p style={{ fontSize: '14px', color: '#9ca3af', marginBottom: '20px' }}>Hiperłącze przekieruje Cię bezpośrednio do dedykowanej oferty zakładu w celu postawienia kuponu.</p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button onClick={confirmRedirect} style={{ backgroundColor: '#10b981', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>Tak</button>
              <button onClick={() => setShowModal({ show: false, url: '' })} style={{ backgroundColor: '#ef4444', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: '6px', cursor: 'pointer' }}>Nie</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ANALITYKA WYKRESÓW CZASU */}
      {showTimeModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 2000 }}>
          <div style={{ backgroundColor: '#1f2937', padding: '24px', borderRadius: '8px', width: '650px', border: '1px solid #3b82f6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ margin: 0 }}>Czas spędzony na wyszukiwaniu ofert</h3>
              <select 
                value={timePeriod} 
                onChange={(e) => setTimePeriod(parseInt(e.target.value))}
                style={{ backgroundColor: '#374151', color: '#fff', border: 'none', padding: '8px', borderRadius: '4px', cursor: 'pointer' }}
              >
                <option value={30}>Ostatnie 30 dni</option>
                <option value={90}>Ostatnie 90 dni</option>
                <option value={365}>Ostatnie 365 dni</option>
              </select>
            </div>
            
            <div style={{ width: '100%', height: '260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeData}>
                  <XAxis dataKey="day" stroke="#9ca3af" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#9ca3af" label={{ value: 'minuty', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#374151', border: 'none', color: '#fff' }} />
                  <Line type="monotone" dataKey="minutes" stroke="#10b981" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={{ textAlign: 'right', marginTop: '16px' }}>
              <button onClick={() => setShowTimeModal(false)} style={{ backgroundColor: '#4b5563', border: 'none', padding: '8px 20px', borderRadius: '6px', color: '#fff', cursor: 'pointer' }}>Zamknij</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}