import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;


public class hsqlinit {

	public static void main(String[] args)
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
			con=DriverManager.getConnection("jdbc:hsqldb:file:/home/ramnatthan/workspace/HSqlApp/databases/mydatabase");
			System.out.println("Got connection");

			String writedelaystmt = "SET FILES WRITE DELAY FALSE";
			java.sql.Statement st2 = con.createStatement();
			st2.execute(writedelaystmt);

			String tableType = ""; // Default is memory, so leave it empty
			
			String createStatement  = "create " + tableType + " table contacts (name varchar(45),email varchar(45),phone varchar(45))";

			con.createStatement().executeUpdate(createStatement);

			System.out.println("Create done");
			
			java.sql.Statement st = con.createStatement();
			st.execute("SHUTDOWN");
		}
		catch (SQLException e) 
		{
			e.printStackTrace(System.out);
		}
	}
}
