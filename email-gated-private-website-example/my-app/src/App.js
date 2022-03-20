/////////////////PROD//////////////////
// npm run build
// PROD: aws s3 cp --recursive build/ s3://emailgatedprivatewebsite-athensemailgateddemobuck-m4jxnh0sa5ep
// PROD: aws cloudfront create-invalidation --distribution-id E26PZJYKAWK606 --paths "/*"
// FFB: aws s3 cp --recursive build/ s3://emailgatedprivatewebsite-athensemailgateddemobuck-m4jxnh0sa5ep && aws cloudfront create-invalidation --distribution-id E26PZJYKAWK606 --paths "/*"

import './App.css'
import React from 'react'

class App extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      email: '',
      authButton: (
        <div
          type="button"
          className="create-layer-button"
          onClick={this.handleSubmit}
        >
          <a href={`${process.env.REACT_APP_CREATE_SIGNED_URL}?email`}>Authenticate</a>
        </div>
      ),
    }
  }

  handleEmailChange(event) {
    const newButton = (
      <div
        type="button"
        className="create-layer-button"
        onClick={this.handleSubmit}
      >
        <a href={`${process.env.REACT_APP_CREATE_SIGNED_URL}?email=${event.target.value}`}>Authenticate</a>
      </div>
    )
    this.setState({ email: event.target.value, authButton: newButton })
  }

  // handleSubmit = (i) => {
  //   console.log('handling submit')
  //   let email = this.state.email
  //   const url = process.env.REACT_APP_CREATE_SIGNED_URL
  //   const final_url = url
  //   fetch(final_url, {
  //     method: 'GET',
  //     mode: 'cors',
  //   }).then((response) => {
  //     console.log(response)
  //   })
  // }

  createUI = () => {
    return (
      <>
        <table className="habit-ui-table">
          <tbody>
            <tr>
              <td>Email*:</td>
              <td className="td-textarea">
                <input
                  placeholder={'email@example.com'}
                  className="bullet-textarea"
                  onChange={this.handleEmailChange.bind(this)}
                />
              </td>
            </tr>

            <tr>
              <td></td>
              <td>
                {this.state.authButton}
                {/* <div
                  type="button"
                  className="create-layer-button"
                  onClick={this.handleSubmit}
                >
                  
                </div> */}
              </td>
            </tr>
          </tbody>
        </table>
      </>
    )
  }

  componentDidMount() {
    // this.getNewEntries()
  }

  componentDidUpdate() {}

  getEditHabitsMode = () => {
    return (
      <div>
        <div className="App">
          <div className="nav-bar-div">
            <span className="left-elem">
              <span className="nav-bar-cell habit-tracker-header">
                Login Form
              </span>
            </span>
          </div>
          {this.createUI()}
        </div>
        <div className="blank-footer" />
      </div>
    )
  }

  getMainView = () => {
    return this.getEditHabitsMode()
  }

  render() {
    return this.getMainView()
  }
}

export default App
