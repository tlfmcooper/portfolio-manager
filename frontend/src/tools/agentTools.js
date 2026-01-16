/**
 * Tool definitions for the Portfolio Pilot agent.
 * These tools allow the agent to control the dashboard state and navigate pages.
 */

export const tools = [
  {
    name: "navigate_to_page",
    description: "Navigate to a specific page in the application.",
    parameters: {
      type: "object",
      properties: {
        page: {
          type: "string",
          enum: ["overview", "portfolio", "analytics", "live-market", "update-portfolio"],
          description: "The page to navigate to."
        }
      },
      required: ["page"]
    }
  },
  {
    name: "set_currency",
    description: "Set the global currency for the dashboard. This affects all charts and values.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "The currency code (USD or CAD)."
        }
      },
      required: ["currency"]
    }
  },
  {
    name: "show_risk_metrics",
    description: "Show risk metrics in the Analytics page. Can optionally set currency.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override for risk metrics."
        }
      }
    }
  },
  {
    name: "show_efficient_frontier",
    description: "Show the Efficient Frontier chart in the Analytics page. Can optionally set currency.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override for efficient frontier."
        }
      }
    }
  },
  {
    name: "run_monte_carlo",
    description: "Run a Monte Carlo simulation with custom parameters.",
    parameters: {
      type: "object",
      properties: {
        scenarios: {
          type: "integer",
          description: "Number of simulation scenarios (e.g., 1000, 5000).",
          minimum: 100,
          maximum: 10000
        },
        time_horizon: {
          type: "integer",
          description: "Time horizon in trading days (e.g., 252 for 1 year).",
          minimum: 20,
          maximum: 1260
        },
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override."
        }
      }
    }
  },
  {
    name: "run_cppi_simulation",
    description: "Run a CPPI (Constant Proportion Portfolio Insurance) simulation with custom parameters.",
    parameters: {
      type: "object",
      properties: {
        multiplier: {
          type: "integer",
          description: "Risk multiplier (e.g., 3, 4, 5). Higher means more aggressive.",
          minimum: 1,
          maximum: 10
        },
        floor: {
          type: "number",
          description: "Floor protection level as a fraction of initial value (e.g., 0.8 for 80%).",
          minimum: 0.5,
          maximum: 0.95
        },
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override."
        }
      }
    }
  },
  {
    name: "get_portfolio_summary",
    description: "Get a summary of the portfolio performance.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency override."
        }
      }
    }
  },
  {
    name: "analyze_portfolio",
    description: "Perform portfolio analysis to answer questions about holdings. Use this to find largest/smallest holdings, best/worst performers, or get a summary of all holdings.",
    parameters: {
      type: "object",
      properties: {
        query_type: {
          type: "string",
          enum: [
            "largest_holding",
            "smallest_holding", 
            "top_performers",
            "worst_performers",
            "holdings_summary",
            "sector_breakdown"
          ],
          description: "Type of analysis: largest_holding (highest market value), smallest_holding (lowest market value), top_performers (best period returns), worst_performers (worst period returns), holdings_summary (all holdings with metrics), sector_breakdown (allocation by sector)."
        },
        period: {
          type: "string",
          enum: ["ytd", "1m", "3m", "1y"],
          description: "Time period for performance calculations. Default is 'ytd' (year-to-date). Options: ytd, 1m (1 month), 3m (3 months), 1y (1 year)."
        },
        limit: {
          type: "integer",
          description: "Number of results for top/worst performers queries. Default is 5.",
          minimum: 1,
          maximum: 50
        },
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency for values."
        }
      },
      required: ["query_type"]
    }
  },
  {
    name: "get_holding_performance",
    description: "Get detailed performance metrics for a specific holding by ticker symbol. Returns YTD, 1-month, 3-month, and 1-year returns along with cost-basis gain/loss. Note: For mutual funds (.CF suffix), only cost-basis returns are available - historical period returns are not accessible.",
    parameters: {
      type: "object",
      properties: {
        ticker: {
          type: "string",
          description: "The ticker symbol of the holding (e.g., AAPL, GOOG, PHN9756.CF)."
        },
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency for values."
        }
      },
      required: ["ticker"]
    }
  },
  {
    name: "get_all_holdings_performance",
    description: "Get performance metrics for ALL holdings in the portfolio at once. Use this when you need to compare holdings or find the best/worst performers. Returns YTD, 1M, 3M, 1Y returns for each holding.",
    parameters: {
      type: "object",
      properties: {
        currency: {
          type: "string",
          enum: ["USD", "CAD"],
          description: "Optional currency for values."
        },
        period: {
          type: "string",
          enum: ["ytd", "1m", "3m", "1y"],
          description: "Primary period of interest. All periods are returned but this helps focus the response."
        }
      }
    }
  }
];

/**
 * Execute a tool call.
 * @param {string} name - The name of the tool.
 * @param {object} args - The arguments for the tool.
 * @param {object} context - The context object containing navigation and agent context functions.
 * @returns {Promise<string>} - The result of the tool execution.
 */
export const executeTool = async (name, args, context) => {
  const { 
    navigate, 
    updateGlobalParams, 
    updateRiskParams, 
    updateFrontierParams, 
    updateMonteCarloParams, 
    updateCPPIParams,
    api // Access to backend API for direct data fetching if needed
  } = context;

  console.log(`[Agent] Executing tool: ${name}`, args);

  try {
    switch (name) {
      case "navigate_to_page":
        navigate(`/dashboard/${args.page}`);
        return `Navigated to ${args.page} page.`;

      case "set_currency":
        updateGlobalParams({ currency: args.currency });
        return `Global currency set to ${args.currency}. Charts will update.`;

      case "show_risk_metrics":
        navigate('/dashboard/analytics?view=risk');
        if (args.currency) {
          updateRiskParams({ currency: args.currency });
        }
        return `Navigated to Analytics (Risk View). Risk metrics updated${args.currency ? ` with currency ${args.currency}` : ''}.`;

      case "show_efficient_frontier":
        navigate('/dashboard/analytics?view=efficient');
        if (args.currency) {
          updateFrontierParams({ currency: args.currency });
        }
        return `Navigated to Analytics (Efficient Frontier View). Chart updated${args.currency ? ` with currency ${args.currency}` : ''}.`;

      case "run_monte_carlo":
        navigate('/dashboard/analytics?view=simulation');
        updateMonteCarloParams(args);
        return `Navigated to Analytics (Monte Carlo View). Simulation running with: ${JSON.stringify(args)}.`;

      case "run_cppi_simulation":
        navigate('/dashboard/analytics?view=strategy');
        updateCPPIParams(args);
        return `Navigated to Analytics (CPPI View). Simulation running with: ${JSON.stringify(args)}.`;

      case "get_portfolio_summary":
        // This tool might return data directly to the LLM to summarize
        // For now, we can just say we fetched it, or actually fetch it if we want the LLM to see the data.
        // Let's actually fetch it so the LLM can answer questions.
        try {
          const response = await api.get('/portfolios/summary', { params: { currency: args.currency } });
          return JSON.stringify(response.data);
        } catch (error) {
          return `Error fetching summary: ${error.message}`;
        }

      case "analyze_portfolio":
        // Perform portfolio analysis based on query_type
        try {
          const params = {
            query_type: args.query_type,
            currency: args.currency,
            period: args.period || 'ytd',
            limit: args.limit || 5
          };
          const response = await api.get('/portfolios/analyze', { params });
          return JSON.stringify(response.data);
        } catch (error) {
          return `Error analyzing portfolio: ${error.message}`;
        }

      case "get_holding_performance":
        // Get performance metrics for a specific holding
        try {
          const ticker = args.ticker.toUpperCase().trim();
          const response = await api.get(`/holdings/${ticker}/performance`, { 
            params: { currency: args.currency } 
          });
          return JSON.stringify(response.data);
        } catch (error) {
          return `Error fetching holding performance: ${error.message}`;
        }

      case "get_all_holdings_performance":
        // Get performance for all holdings in batch
        try {
          const response = await api.get('/holdings/performance/batch', { 
            params: { 
              currency: args.currency,
              period: args.period || 'ytd'
            } 
          });
          return JSON.stringify(response.data);
        } catch (error) {
          return `Error fetching holdings performance: ${error.message}`;
        }

      default:
        return `Unknown tool: ${name}`;
    }
  } catch (error) {
    console.error(`[Agent] Error executing ${name}:`, error);
    return `Error executing tool ${name}: ${error.message}`;
  }
};
