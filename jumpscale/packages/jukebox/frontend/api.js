// const axios = require('axios')
const baseURL = "/jukebox/api"

const apiClient = {
  content: {
    get: (url) => {
      return axios({
        url: url
      })
    }
  },
  server: {
    isRunning: () => {
      return axios({
        url: `${baseURL}/status`,
        method: "get"
      })
    }
  },
  admins: {
    getCurrentUser: () => {
      return axios({
        url: "/auth/authenticated/"
      })
    },
  },
  solutions: {
    getSolutions: (solutionType) => {
      return axios({
        url: `${baseURL}/deployments/${solutionType}`,
        method: "get",
      })
    },
    cancelDeployment: (name, solutionType) => {
      return axios({
        url: `${baseURL}/deployments/cancel/`,
        method: "post",
        data: { name: name, solution_type: solutionType },
        headers: { 'Content-Type': 'application/json' }
      })
    },
    switchAutoExtend: (name, solutionType, newState) => {
      return axios({
        url: `${baseURL}/deployments/switch_auto_extend/`,
        method: "post",
        data: { name: name, solution_type: solutionType, new_state: newState },
        headers: { 'Content-Type': 'application/json' }
      })
    },

  },
  wallet: {
    getTopupInfo: () => {
      return axios({
        url: `${baseURL}//wallet`,
        method: "get",
      })
    },
  },
  license: {
    accept: () => {
      return axios({
        url: `${baseURL}/accept/`,
        method: "get"
      })
    },
  },


}
