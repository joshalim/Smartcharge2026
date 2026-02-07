import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Custom hook for OCPP WebSocket connection
 * Provides real-time updates for charger status, transactions, and events
 */
export function useOCPPWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const [onlineChargers, setOnlineChargers] = useState(0);
  const [chargerStatuses, setChargerStatuses] = useState({});
  const [activeTransactions, setActiveTransactions] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const listenersRef = useRef([]);

  // Get WebSocket URL from environment or use default
  const getWsUrl = useCallback(() => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    // Convert http(s) to ws(s)
    const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
    const host = backendUrl.replace(/^https?:\/\//, '');
    return `${wsProtocol}://${host}/api/ocpp/ws`;
  }, []);

  // Add event listener
  const addEventListener = useCallback((callback) => {
    listenersRef.current.push(callback);
    return () => {
      listenersRef.current = listenersRef.current.filter(cb => cb !== callback);
    };
  }, []);

  // Notify all listeners
  const notifyListeners = useCallback((event) => {
    listenersRef.current.forEach(callback => {
      try {
        callback(event);
      } catch (e) {
        console.error('Error in OCPP event listener:', e);
      }
    });
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = getWsUrl();
    console.log('Connecting to OCPP WebSocket:', wsUrl);

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('OCPP WebSocket connected');
        setConnected(true);
        // Request initial status
        wsRef.current.send('status');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('OCPP WebSocket message:', data);
          
          setLastEvent(data);
          notifyListeners(data);

          // Update state based on event type
          if (data.event === 'status') {
            setOnlineChargers(data.online_chargers || 0);
            if (data.chargers) {
              const statuses = {};
              data.chargers.forEach(c => {
                statuses[c.charger_id] = c;
              });
              setChargerStatuses(statuses);
            }
          } else if (data.event === 'charger_connected') {
            setOnlineChargers(prev => prev + 1);
            setChargerStatuses(prev => ({
              ...prev,
              [data.data.charger_id]: { 
                charger_id: data.data.charger_id, 
                connected: true, 
                status: 'Available' 
              }
            }));
          } else if (data.event === 'charger_disconnected') {
            setOnlineChargers(prev => Math.max(0, prev - 1));
            setChargerStatuses(prev => {
              const newStatuses = { ...prev };
              if (newStatuses[data.data.charger_id]) {
                newStatuses[data.data.charger_id].connected = false;
              }
              return newStatuses;
            });
          } else if (data.event === 'transaction_started') {
            setActiveTransactions(prev => [...prev, data.data]);
            setChargerStatuses(prev => ({
              ...prev,
              [data.data.charger_id]: {
                ...prev[data.data.charger_id],
                status: 'Charging'
              }
            }));
          } else if (data.event === 'transaction_stopped') {
            setActiveTransactions(prev => 
              prev.filter(tx => tx.transaction_id !== data.data.transaction_id)
            );
            setChargerStatuses(prev => ({
              ...prev,
              [data.data.charger_id]: {
                ...prev[data.data.charger_id],
                status: 'Available'
              }
            }));
          }
        } catch (e) {
          console.error('Error parsing OCPP WebSocket message:', e);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('OCPP WebSocket closed:', event.code, event.reason);
        setConnected(false);
        
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect OCPP WebSocket...');
          connect();
        }, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('OCPP WebSocket error:', error);
      };

    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      // Retry connection after 5 seconds
      reconnectTimeoutRef.current = setTimeout(connect, 5000);
    }
  }, [getWsUrl, notifyListeners]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  // Send message to WebSocket
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, []);

  // Request status update
  const requestStatus = useCallback(() => {
    sendMessage('status');
  }, [sendMessage]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Send ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (!connected) return;
    
    const pingInterval = setInterval(() => {
      sendMessage('ping');
    }, 30000);

    return () => clearInterval(pingInterval);
  }, [connected, sendMessage]);

  return {
    connected,
    lastEvent,
    onlineChargers,
    chargerStatuses,
    activeTransactions,
    connect,
    disconnect,
    sendMessage,
    requestStatus,
    addEventListener
  };
}

export default useOCPPWebSocket;
