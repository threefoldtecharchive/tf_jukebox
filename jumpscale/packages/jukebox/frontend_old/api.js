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
    list: ()=>{
      return axios({
        url: `${baseURL}/admins/list`
    })
    },
    add: (name) => {
      return axios({
          url: `${baseURL}/admins/add`,
          method: "post",
          headers: { 'Content-Type': 'application/json' },
          data: { name: name }
      })
    },
    remove: (name) => {
      return axios({
          url: `${baseURL}/admins/remove`,
          method: "post",
          headers: { 'Content-Type': 'application/json' },
          data: { name: name }
      })}
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
