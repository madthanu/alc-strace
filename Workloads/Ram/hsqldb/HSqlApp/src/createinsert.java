import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Savepoint;

public class createinsert {

	public static void createAndInsert(boolean create, boolean update, boolean isCachedTable, boolean useSavePoints) throws SQLException
	{
		Connection con = null; 

		try 
		{
			Class.forName("org.hsqldb.jdbc.JDBCDriver");
		} 
		catch (ClassNotFoundException e)
		{
			e.printStackTrace(System.out);
		}

		try
		{
			System.out.println("Getting connection");
			con=DriverManager.getConnection("jdbc:hsqldb:file:/home/ramnatthan/workspace/HSqlApp/databases/mydatabase;shutdown=true");
			//System.out.println("Got connection");

			//String writedelaystmt = "SET FILES WRITE DELAY FALSE";
			//java.sql.Statement st = con.createStatement();
			//st.execute(writedelaystmt);
			
			String tableType = ""; // Default is memory, so leave it empty
			if(isCachedTable)
			{
				tableType = "cached";
			}

			String createStatement  = "create " + tableType + " table contacts (name varchar(45),email varchar(45),phone varchar(45))";
			
			if(create)
			{
				con.createStatement().executeUpdate(createStatement);
				//System.out.println("Create done");
			}
		}
		catch (SQLException e) 
		{
			e.printStackTrace(System.out);
		}

		Savepoint[] sp = new Savepoint[10];
		int savepointindex=0; 
		PreparedStatement pst1 = null;
		try
		{
			// Start of the transaction
			//System.out.println("Txn starting");
			con.setAutoCommit(false);

			//if(create)
			{
				for(int loop = 0;loop<=100;loop++)
				{
					pst1=con.prepareStatement("insert into contacts values(?,?,?)");
					pst1.clearParameters();
					pst1.setString(1, String.format("name%d", loop));
					pst1.setString(2, String.format("email%d@cs.wisc.edu", loop));
					pst1.setString(3, String.format("%d", loop));
					pst1.executeUpdate();
					
					if(useSavePoints)
					{
						if(loop % 30 == 0)
						{
							//System.out.println("Setting a save point");
							sp[savepointindex++] = con.setSavepoint();
							//System.out.println("Save point - Done");
						}
					}
				}
			}

			if(update)
			{
				for(int loop = 0;loop<=50;loop++)
				{
					pst1=con.prepareStatement("update contacts set phone = ? where name = ?");
					pst1.clearParameters();

					pst1.setString(2, String.format("name%d", loop));
					pst1.setString(1, String.format("%d updated", loop));
					pst1.executeUpdate();
				}
			}

			if (useSavePoints)
			{
				//System.out.println("Txn Rollingback to sp0");
				con.rollback(sp[1]);
				//System.out.println("Txn Rollback to sp0 done");
			}
			else
			{
				con.commit();
				System.out.println("TXNCommitDone");
			}
			// End of transaction
		}
		catch (SQLException e) 
		{
			e.printStackTrace(System.out);
		}
		finally
		{
			if(pst1 != null)
			{
				//System.out.println("Closing statement");
				pst1.close();
				//System.out.println("Closed statement");
			}

			//System.out.println("Setting auto commit to true back");
			con.setAutoCommit(true);
			//System.out.println("Setting auto commit to true back - Done");

			//System.out.println("Going to execute shutdown");
			java.sql.Statement st = con.createStatement();
			st.execute("SHUTDOWN");
			//System.out.println("shutdown done");

			//System.out.println("Closing connection");
			con.close();
			//System.out.println("Closed connection");
		}
	}
}